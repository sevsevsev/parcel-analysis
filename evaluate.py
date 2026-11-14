#!/usr/bin/env python3
"""Evaluate a listing from an address or parcel ids, from the command line (no web server needed).

Examples:
  python3 evaluate.py --address "331 Barren Hill Rd, Conshohocken PA" --preset build
  python3 evaluate.py --address "331 Barren Hill Rd, Conshohocken PA" --neighbors      # list parcels nearby, then:
  python3 evaluate.py --county 42091 --parcels 650000463003,650000454003 --preset full --pdf --title "Barren Hill Rd"
  python3 evaluate.py --listing barren_hill                                            # rerun a saved listing

Writes listings/web/<id>.yaml and outputs/web/<id>/ (report.html, atlas.pdf when --pdf, evaluation.md, GeoPackages).
"""
import argparse
import secrets
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from app import geo, pipeline, registry  # noqa: E402


def neighbors(lat, lon, fips, radius_m=120):
    """Parcels within radius_m of a point, nearest first (for picking neighbours by hand)."""
    import httpx
    from shapely.geometry import Point, shape
    c = registry.county(fips)
    src = registry.catalog()["overlays"][c["parcels"]["use"]]
    pc = c["parcels"]
    d = radius_m / 111_000.0
    fields = [f for f in (pc["id_field"], pc.get("label_field"), pc.get("acres_field")) if f]
    r = httpx.get(src["url"].rstrip("/") + "/query", params={
        "geometry": f"{lon - d},{lat - d},{lon + d},{lat + d}", "geometryType": "esriGeometryEnvelope", "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects", "outFields": ",".join(fields), "returnGeometry": "true", "outSR": 4326, "f": "geojson"},
        headers=geo.UA, timeout=60)
    r.raise_for_status()
    pt = Point(lon, lat)
    rows = []
    for f in r.json().get("features") or []:
        g = shape(f["geometry"]) if f.get("geometry") else None
        p = f.get("properties") or {}
        rows.append((g.distance(pt) * 111_000 if g else 9e9, str(p.get(pc["id_field"])), str(p.get(pc.get("label_field")) or ""),
                     p.get(pc.get("acres_field")) if pc.get("acres_field") else None))
    return sorted(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--address", help="street address; the parcel nearest the geocoded point is used")
    ap.add_argument("--county", help="county FIPS (e.g. 42091 Montgomery, 42101 Philadelphia); inferred from --address")
    ap.add_argument("--parcels", help="comma-separated parcel ids to evaluate (adds to the address parcel if both given)")
    ap.add_argument("--neighbors", action="store_true", help="list parcels within 120 m of the address and exit")
    ap.add_argument("--preset", default="build", choices=registry.PRESETS, help="which layers to pull (default build)")
    ap.add_argument("--layers", help="comma-separated catalog keys instead of a preset")
    ap.add_argument("--title")
    ap.add_argument("--pdf", action="store_true", help="also build atlas.pdf")
    ap.add_argument("--listing", help="rerun an existing listing name (listings/<name>.yaml or listings/web/<id>.yaml)")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="override an evaluation threshold, e.g. --set max_build_slope_pct=25 --set property_line_setback_ft=75")
    a = ap.parse_args()

    if a.listing:
        cfg_path = ROOT / "listings" / f"{a.listing}.yaml"
        if not cfg_path.exists():
            cfg_path = ROOT / "listings" / "web" / f"{a.listing}.yaml"
        if not cfg_path.exists():
            sys.exit(f"no listing named {a.listing}")
        name = a.listing
    else:
        fips, ids = a.county, []
        if a.address:
            g = geo.geocode(a.address)
            if not g:
                sys.exit("address not found by the Census geocoder; try adding the town and state")
            print(f"geocoded: {g['matched']}  ({g['county_name']}, FIPS {g['county_fips']})")
            fips = fips or g["county_fips"]
            if not registry.county(fips):
                sys.exit(f"county {fips} is not in counties.yaml; add its parcel service there first")
            if a.neighbors:
                print("parcels near the address (distance m, id, address, acres):")
                for dist, pid, lab, ac in neighbors(g["lat"], g["lon"], fips):
                    print(f"  {dist:6.0f}  {pid:16s} {lab:34s} {ac if ac is not None else ''}")
                return
            p = geo.parcel_by_address(fips, g["matched"] or a.address) or geo.parcel_at(g["lat"], g["lon"], fips)
            if not p:
                sys.exit("no parcel matches that address or lies within 40 m of the geocoded point; use --neighbors or --parcels")
            print(f"parcel {'matched by address' if p.get('matched_by') == 'address' else 'nearest the geocoded point'}: "
                  f"{p['parcel_id']}  {p['label']}  {p['acres']} ac")
            ids.append(p["parcel_id"])
        if a.parcels:
            ids += [x.strip() for x in a.parcels.split(",") if x.strip()]
        if not ids or not fips:
            sys.exit("give --address, or --county and --parcels")
        ids = list(dict.fromkeys(ids))
        layers = [x.strip() for x in a.layers.split(",")] if a.layers else registry.presets_for(fips)[a.preset]
        thresholds = {}
        for kv in a.set:
            k, v = kv.split("=", 1)
            thresholds[k] = float(v) if v.replace(".", "", 1).isdigit() else v
        name = secrets.token_hex(4)
        cfg = registry.build_listing_config(name, fips, ids, layers, thresholds, None, a.title)
        (ROOT / "listings" / "web").mkdir(parents=True, exist_ok=True)
        cfg_path = ROOT / "listings" / "web" / f"{name}.yaml"
        cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
        print(f"listing {name}: {len(ids)} parcel(s), {len(layers)} layers -> {cfg_path.relative_to(ROOT)}")

    t0 = time.time()

    def progress(step, i, n):
        if step != "done":
            print(f"[{i + 1}/{n}] {step}", flush=True)

    pipeline.run_listing(cfg_path, progress, lambda line: None, pdf=a.pdf)
    out = ROOT / yaml.safe_load(open(cfg_path)).get("output_dir", f"outputs/{name}")
    print(f"done in {time.time() - t0:.0f} s. Outputs in {out.relative_to(ROOT)}/: report.html, evaluation.md"
          + (", atlas.pdf" if a.pdf else "") + ", property.gpkg, evaluation.gpkg")
    ej = out / "evaluation.json"
    if ej.exists():
        import json
        E = json.loads(ej.read_text())
        B, G, S = E["buildable"], E.get("growing") or {}, E["sun"]
        print(f"  {B['property_acres']:.2f} ac; buildable {B['buildable_acres']:.2f} ac ({B['buildable_pct']}%); "
              f"garden {G.get('garden_acres', 0):.2f} ac; usable {G.get('usable_pct', 0)}%; winter solar index "
              f"{S.get('dec21_solar_index_buildable')}; run-on {E['stormwater']['runon_from_offsite_acres']:.1f} ac")


if __name__ == "__main__":
    main()
