"""County registry, source catalog and listing-config builder for the web app."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PRESETS = ["quick", "build", "grow", "full"]


def catalog() -> dict:
    return yaml.safe_load(open(ROOT / "sources.yaml"))


def counties() -> dict:
    return yaml.safe_load(open(ROOT / "counties.yaml"))


def template() -> dict:
    return yaml.safe_load(open(ROOT / "listings" / "_template.yaml"))


def county(fips: str) -> dict | None:
    return counties()["counties"].get(str(fips))


def layer_keys_for(fips: str) -> list[str]:
    reg, c = counties(), county(fips)
    if not c:
        return []
    keys = list(reg.get("national", [])) + list(reg.get("state_layers", {}).get(c.get("state", ""), [])) + list(c.get("layers", []))
    drop = set(c.get("drop_layers", []))
    return [k for k in dict.fromkeys(keys) if k not in drop]


def layer_info(fips: str) -> list[dict]:
    cat = catalog()
    out = []
    for k in layer_keys_for(fips):
        spec = cat["overlays"].get(k) or cat["rasters"].get(k)
        if not spec:
            continue
        out.append({"key": k, "description": spec.get("description", k), "group": spec.get("group", "context"),
                    "preset": spec.get("presets", []), "typical_seconds": spec.get("typical_seconds", 2),
                    "kind": "raster" if k in cat["rasters"] else "overlay", "role": spec.get("role")})
    return out


def presets_for(fips: str) -> dict:
    info = layer_info(fips)
    return {p: [l["key"] for l in info if p in l["preset"]] for p in PRESETS}


def parcel_where(c: dict, parcel_ids: list[str]) -> str:
    pc = c["parcels"]
    extra = f" AND ({pc['filter_where']})" if pc.get("filter_where") else ""
    if pc.get("id_fields"):   # composite id "a-b" -> (f1='a' AND f2='b') OR ...
        parts = []
        for pid in parcel_ids:
            vals = str(pid).split("-", len(pc["id_fields"]) - 1)
            parts.append("(" + " AND ".join(f"{f} = '{v.replace(chr(39), chr(39) * 2)}'" for f, v in zip(pc["id_fields"], vals)) + ")")
        return "(" + " OR ".join(parts) + ")" + extra
    f = pc["id_field"]
    if pc.get("id_type") == "integer":
        ids = ",".join(str(int(re.sub(r"\D", "", str(i)))) for i in parcel_ids)
        return f"{f} IN ({ids})" + extra
    ids = ",".join("'" + str(i).replace("'", "''") + "'" for i in parcel_ids)
    return f"{f} IN ({ids})" + extra


def build_listing_config(listing_id: str, fips: str, parcel_ids: list[str], layers: list[str],
                         thresholds: dict | None, growing: dict | None, title: str | None) -> dict:
    """A listing YAML (as a dict) that the pipeline can run, with parcels pulled from the county service."""
    c = county(fips)
    if not c:
        raise ValueError(f"county {fips} is not registered")
    cat = catalog()
    tpl = template()
    pc = c["parcels"]
    parcels_spec = {"source": "arcgis", "url": cat["overlays"][pc["use"]]["url"], "where": parcel_where(c, parcel_ids),
                    "out_fields": cat["overlays"][pc["use"]].get("out_fields", "*"),
                    "id_field": pc["id_field"], "acres_field": pc.get("acres_field"), "label_field": pc.get("label_field"),
                    "keep_fields": pc.get("keep_fields")}
    if pc.get("derive_fields"):
        parcels_spec["derive_fields"] = dict(pc["derive_fields"])
    for k in ("assessment_field", "tax_fields"):
        if pc.get(k):
            parcels_spec[k] = pc[k]
    allowed = set(layer_keys_for(fips))
    chosen = [k for k in layers if k in allowed]
    overlays = [{"use": k} for k in chosen if k in cat["overlays"]]
    rasters = [{"use": k} for k in chosen if k in cat["rasters"]]
    ev = dict(tpl.get("evaluation", {}))
    ev.update(c.get("evaluation", {}))
    ev.update({k: v for k, v in (thresholds or {}).items() if v is not None})
    gw = dict(tpl.get("growing", {}))
    gw.update({k: v for k, v in (growing or {}).items() if v is not None})
    cfg = {"name": listing_id, "title": title or f"{len(parcel_ids)} parcel(s), {c['name']}", "crs": c.get("crs", "EPSG:2272"),
           "aoi_buffer_ft": tpl.get("aoi_buffer_ft", 500), "output_dir": f"outputs/web/{listing_id}",
           "cache_dir": f"data/cache/web/{listing_id}", "notes": c.get("notes", ""),
           "parcels": parcels_spec, "overlays": overlays, "rasters": rasters, "evaluation": ev, "growing": gw,
           "qa": tpl.get("qa", {}), "maps": {**tpl.get("maps", {}), "dpi": 120}, "county_fips": str(fips)}
    return cfg
