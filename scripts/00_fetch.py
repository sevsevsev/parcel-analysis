"""Materialise every remote source in config into data/cache/ so the rest of the pipeline only
reads local files. Writes outputs/sources.md documenting where each layer came from and when.

Order: parcels (if remote, by `where` filter) -> area of interest (AOI) from parcels -> overlays and
rasters by AOI bounding box. Cached layers are reused unless --refresh is given.
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
from pyproj import CRS

sys.path.insert(0, str(Path(__file__).parent))
from _common import cache_dir, cache_path, crs_unit_to_feet, load_config, write_md  # noqa: E402
import _fetch  # noqa: E402

REFRESH = "--refresh" in sys.argv


def is_remote(spec):
    return spec.get("source", "file") != "file"


def cached(cfg, spec):
    p = cache_path(cfg, spec)
    return p.exists() and not REFRESH


def meta_path(cfg, spec):
    return cache_path(cfg, spec).with_suffix(".json")


def fetch_vector(cfg, spec, bbox4326):
    src, name = spec["source"], spec["name"]
    out = cache_path(cfg, spec)
    if cached(cfg, spec):
        print(f"[{name}] cached: {out.name}")
        return
    print(f"[{name}] fetching ({src})")
    if src == "arcgis":
        gdf, info = _fetch.fetch_arcgis_features(spec["url"], None if spec.get("where_only") else bbox4326,
                                                 spec.get("where", "1=1"), spec.get("out_fields", "*"))
    elif src == "wfs":
        gdf, info = _fetch.fetch_wfs(spec["url"], spec["typename"], bbox4326)
    elif src == "url":
        path, info = _fetch.download_url(spec["url"], cache_dir(cfg), name)
        gdf = gpd.read_file(path, **({"layer": spec["layer"]} if spec.get("layer") else {}))
    else:
        sys.exit(f"unknown source '{src}' for {name}")
    if len(gdf) == 0:
        print(f"  WARNING: {name} returned no features for the AOI")
    gdf.to_file(out, driver="GPKG")
    meta_path(cfg, spec).write_text(json.dumps(info, indent=2))
    print(f"  saved {out.relative_to(cfg['_root'])} ({len(gdf)} features)")


def fetch_raster(cfg, spec, bbox_proj):
    name, out = spec["name"], cache_path(cfg, spec)
    if cached(cfg, spec):
        print(f"[{name}] cached: {out.name}")
        return
    print(f"[{name}] fetching ({spec['source']})")
    if spec["source"] == "arcgis_image":
        epsg = CRS(cfg["crs"]).to_epsg()
        info = _fetch.fetch_arcgis_image(spec["url"], bbox_proj, epsg, float(spec.get("resolution", 10)), out,
                                         spec.get("pixel_type", "F32"))
    elif spec["source"] == "url":
        path, info = _fetch.download_url(spec["url"], cache_dir(cfg), name)
        if path != out:
            out.write_bytes(path.read_bytes())
    else:
        sys.exit(f"unknown raster source '{spec['source']}' for {name}")
    meta_path(cfg, spec).write_text(json.dumps(info, indent=2))
    print(f"  saved {out.relative_to(cfg['_root'])}")


def main():
    cfg = load_config()
    cache_dir(cfg).mkdir(parents=True, exist_ok=True)
    pspec = dict(cfg["parcels"], name="parcels")

    # 1. parcels
    if is_remote(pspec):
        if not pspec.get("where"):
            sys.exit("Remote parcels need a `where` filter (e.g. \"PIN IN ('a','b')\") so only your parcels are fetched.")
        pspec["where_only"] = True
        fetch_vector(cfg, pspec, None)
        parcels = gpd.read_file(cache_path(cfg, pspec))
    else:
        p = cfg["_root"] / pspec["path"]
        parcels = gpd.read_file(p, **({"layer": pspec["layer"]} if pspec.get("layer") else {}))
    parcels = parcels.to_crs(cfg["crs"])

    # 2. AOI = parcels bounding box + buffer
    k = crs_unit_to_feet(CRS(cfg["crs"]))
    buf = float(cfg.get("aoi_buffer_ft", 500)) / k
    minx, miny, maxx, maxy = parcels.total_bounds
    bbox_proj = (minx - buf, miny - buf, maxx + buf, maxy + buf)
    aoi = gpd.GeoSeries.from_xy([bbox_proj[0], bbox_proj[2]], [bbox_proj[1], bbox_proj[3]], crs=cfg["crs"]).to_crs(4326)
    bbox4326 = (aoi.x.min(), aoi.y.min(), aoi.x.max(), aoi.y.max())
    print(f"AOI (project CRS): {tuple(round(v, 1) for v in bbox_proj)}  buffer {cfg.get('aoi_buffer_ft', 500)} ft")

    # 3. overlays and rasters
    failures = {}
    for spec in cfg.get("overlays") or []:
        if is_remote(spec):
            try:
                fetch_vector(cfg, spec, bbox4326)
            except Exception as e:  # noqa: BLE001  one dead service must not stop the run
                failures[spec["name"]] = f"{type(e).__name__}: {e}"
                print(f"  FAILED {spec['name']}: {failures[spec['name']]}")
    for spec in cfg.get("rasters") or []:
        if is_remote(spec):
            try:
                fetch_raster(cfg, spec, bbox_proj)
            except Exception as e:  # noqa: BLE001
                failures[spec["name"]] = f"{type(e).__name__}: {e}"
                print(f"  FAILED {spec['name']}: {failures[spec['name']]}")

    # 4. provenance
    lines = ["# Data sources", "", "| layer | source | detail | fetched | features / size |", "|---|---|---|---|---|"]
    for spec in [pspec] + list(cfg.get("overlays") or []) + list(cfg.get("rasters") or []):
        if is_remote(spec):
            mp = meta_path(cfg, spec)
            info = json.loads(mp.read_text()) if mp.exists() else {}
            detail = info.get("url", "")
            if info.get("where") and info["where"] != "1=1":
                detail += f" where `{info['where']}`"
            n = info.get("features", info.get("size_px", ""))
            lines.append(f"| {spec['name']} | {spec['source']} | {detail} | {info.get('fetched_at', '')} | {n} |")
        else:
            lines.append(f"| {spec['name']} | file | `{spec.get('path')}`"
                         f"{(' :: ' + spec['layer']) if spec.get('layer') else ''} | | |")
    if failures:
        lines += ["", "## Fetch failures (layer skipped downstream; rerun with --refresh later)", ""]
        lines += [f"- **{k}**: {v}" for k, v in failures.items()]
    write_md(cfg["_out"] / "sources.md", "\n".join(lines) + "\n")
    if failures:
        print(f"\n{len(failures)} remote layer(s) failed: {', '.join(failures)}. Pipeline continues without them.")


if __name__ == "__main__":
    main()
