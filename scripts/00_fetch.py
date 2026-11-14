"""Materialise every remote source in config into data/cache/ so the rest of the pipeline only
reads local files. Writes outputs/sources.md documenting where each layer came from and when.

Order: parcels (if remote, by `where` filter) -> area of interest (AOI) from parcels -> overlays and
rasters by AOI bounding box. Cached layers are reused unless --refresh is given.
"""
import json
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import geopandas as gpd
import pandas as pd
from pyproj import CRS

sys.path.insert(0, str(Path(__file__).parent))
from _common import cache_dir, cache_path, crs_unit_to_feet, find_spec, load_config, write_md  # noqa: E402
import _fetch  # noqa: E402

REFRESH = "--refresh" in sys.argv


def is_remote(spec):
    return spec.get("source", "file") != "file"


def cached(cfg, spec):
    p = cache_path(cfg, spec)
    return p.exists() and not REFRESH


# Shared, location-keyed cache: the same AOI cell fetched for another listing is reused until the
# source's ttl_days expire. Parcels (fetched by `where`) are never shared.
def shared_dir(cfg):
    return cfg["_root"] / "data" / "cache" / "_shared"


def shared_path(cfg, spec, key):
    ext = ".tif" if spec.get("source") == "arcgis_image" else ".gpkg"
    return shared_dir(cfg) / spec["name"] / f"{key}{ext}"


def shared_fresh(cfg, spec, key):
    p = shared_path(cfg, spec, key)
    if not p.exists() or REFRESH:
        return False
    ttl = float(spec.get("ttl_days", 30))
    return (time.time() - p.stat().st_mtime) < ttl * 86400


def use_shared(cfg, spec, key):
    """Copy a fresh shared file (and its metadata) into the listing cache. True if done."""
    if not shared_fresh(cfg, spec, key):
        return False
    sp = shared_path(cfg, spec, key)
    out = cache_path(cfg, spec)
    shutil.copyfile(sp, out)
    if sp.with_suffix(".json").exists():
        shutil.copyfile(sp.with_suffix(".json"), meta_path(cfg, spec))
    print(f"[{spec['name']}] shared cache: {sp.name}")
    return True


def store_shared(cfg, spec, key):
    sp = shared_path(cfg, spec, key)
    sp.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(cache_path(cfg, spec), sp)
    if meta_path(cfg, spec).exists():
        shutil.copyfile(meta_path(cfg, spec), sp.with_suffix(".json"))


def meta_path(cfg, spec):
    return cache_path(cfg, spec).with_suffix(".json")


def fetch_vector(cfg, spec, bbox4326, key=None):
    src, name = spec["source"], spec["name"]
    out = cache_path(cfg, spec)
    if cached(cfg, spec):
        print(f"[{name}] cached: {out.name}")
        return
    if key and use_shared(cfg, spec, key):
        return
    print(f"[{name}] fetching ({src})")
    if src == "arcgis":
        gdf, info = _fetch.fetch_arcgis_features(spec["url"], None if spec.get("where_only") else bbox4326,
                                                 spec.get("where", "1=1"), spec.get("out_fields", "*"))
    elif src == "wfs":
        gdf, info = _fetch.fetch_wfs(spec["url"], spec["typename"], bbox4326,
                                     spec.get("version", "1.1.0"), spec.get("output_format", "GML3"))
    elif src == "ssurgo":
        gdf, info = _fetch.fetch_ssurgo(spec["url"], bbox4326)
    elif src == "url":
        path, info = _fetch.download_url(spec["url"], cache_dir(cfg), name)
        gdf = gpd.read_file(path, **({"layer": spec["layer"]} if spec.get("layer") else {}))
    else:
        sys.exit(f"unknown source '{src}' for {name}")
    if len(gdf) == 0:
        print(f"  WARNING: {name} returned no features for the AOI")
    for lk in spec.get("lookups") or []:
        try:
            gdf = _fetch.apply_lookup(gdf, spec["class_field"], lk)
        except Exception as e:  # noqa: BLE001
            print(f"  lookup {lk.get('url', '')[-60:]} failed: {e}")
    if spec.get("describe_template") and len(gdf):
        gdf[spec.get("describe_field", "description")] = gdf.apply(
            lambda r: spec["describe_template"].format(**{k: ("" if pd.isna(r.get(k)) else r.get(k)) for k in r.index}), axis=1)
    gdf.to_file(out, driver="GPKG")
    info["cache_key"] = key
    meta_path(cfg, spec).write_text(json.dumps(info, indent=2))
    print(f"  saved {out.relative_to(cfg['_root'])} ({len(gdf)} features)")
    if key:
        store_shared(cfg, spec, key)


def fetch_raster(cfg, spec, bbox_proj, key=None):
    name, out = spec["name"], cache_path(cfg, spec)
    if cached(cfg, spec):
        print(f"[{name}] cached: {out.name}")
        return
    key = f"{key}_r{spec.get('resolution', 10)}" if key else None
    if key and use_shared(cfg, spec, key):
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
    info["cache_key"] = key
    meta_path(cfg, spec).write_text(json.dumps(info, indent=2))
    print(f"  saved {out.relative_to(cfg['_root'])}")
    if key:
        store_shared(cfg, spec, key)


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

    # 2. AOI = parcels bounding box + buffer, snapped outward to a grid so nearby listings share
    #    the same cached fetches (and the same DEM, slope and sun rasters).
    k = crs_unit_to_feet(CRS(cfg["crs"]))
    buf = float(cfg.get("aoi_buffer_ft", 500)) / k
    snap = float(cfg.get("aoi_snap_ft", 500)) / k
    minx, miny, maxx, maxy = parcels.total_bounds
    import math
    bbox_proj = (math.floor((minx - buf) / snap) * snap, math.floor((miny - buf) / snap) * snap,
                 math.ceil((maxx + buf) / snap) * snap, math.ceil((maxy + buf) / snap) * snap)
    epsg = CRS(cfg["crs"]).to_epsg()
    key = f"{epsg}_{int(bbox_proj[0])}_{int(bbox_proj[1])}_{int(bbox_proj[2])}_{int(bbox_proj[3])}"
    aoi = gpd.GeoSeries.from_xy([bbox_proj[0], bbox_proj[2]], [bbox_proj[1], bbox_proj[3]], crs=cfg["crs"]).to_crs(4326)
    bbox4326 = (aoi.x.min(), aoi.y.min(), aoi.x.max(), aoi.y.max())
    print(f"AOI (project CRS): {tuple(round(v, 1) for v in bbox_proj)}  buffer {cfg.get('aoi_buffer_ft', 500)} ft")

    # 3. overlays and rasters
    failures = {}

    def job(spec, kind):
        try:
            if kind == "vector":
                fetch_vector(cfg, spec, bbox4326, key)
            else:
                fetch_raster(cfg, spec, bbox_proj, key)
        except Exception as e:  # noqa: BLE001  one dead service must not stop the run
            failures[spec["name"]] = f"{type(e).__name__}: {e}"
            print(f"  FAILED {spec['name']}: {failures[spec['name']]}")

    jobs = [(spec, "vector") for spec in cfg.get("overlays") or [] if is_remote(spec)]
    jobs += [(spec, "raster") for spec in cfg.get("rasters") or [] if is_remote(spec)]
    workers = int(cfg.get("fetch_workers", 6))
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        list(ex.map(lambda j: job(*j), jobs))

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
        dem = find_spec(cfg, "dem", "rasters")
        if dem and dem["name"] in failures:
            sys.exit(f"The elevation service failed ({failures[dem['name']]}); terrain, sun, stormwater and the "
                     "site evaluation need it. Try again in a few minutes.")


if __name__ == "__main__":
    main()
