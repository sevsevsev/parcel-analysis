"""Shared helpers: config loading, layer reading, unit conversion, output paths."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import geopandas as gpd
import yaml
from pyproj import CRS

ROOT = Path(__file__).resolve().parents[1]


def load_config() -> dict:
    """Read config.yaml (or the file named in PROPERTY_CONFIG)."""
    cfg_path = Path(os.environ.get("PROPERTY_CONFIG", ROOT / "config.yaml"))
    if not cfg_path.is_absolute():
        cfg_path = ROOT / cfg_path
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)
    name = cfg.get("name") or cfg_path.stem
    cfg["name"] = name
    cfg["_root"] = ROOT
    cfg["_out"] = ROOT / cfg.get("output_dir", f"outputs/{name}")
    cfg["_out"].mkdir(parents=True, exist_ok=True)
    cfg.setdefault("cache_dir", f"data/cache/{name}")
    _expand_sources(cfg)
    return cfg


def _expand_sources(cfg: dict):
    """Replace `- use: <key>` entries with the catalog entry from sources.yaml, letting the
    listing override any field. Every entry ends up with a `name`."""
    cat_path = ROOT / "sources.yaml"
    catalog = yaml.safe_load(open(cat_path)) if cat_path.exists() else {}
    for section in ("overlays", "rasters"):
        out = []
        for spec in cfg.get(section) or []:
            if "use" in spec:
                key = spec["use"]
                base = (catalog.get(section) or {}).get(key)
                if base is None:
                    sys.exit(f"sources.yaml has no {section} entry '{key}'")
                merged = {**base, **{k: v for k, v in spec.items() if k != "use"}}
                merged.setdefault("name", key)
                out.append(merged)
            else:
                out.append(spec)
        cfg[section] = out


def crs_unit_to_feet(crs: CRS) -> float:
    """Multiplier converting one linear unit of `crs` to feet."""
    unit = crs.axis_info[0].unit_name.lower()
    if "foot" in unit or "feet" in unit:
        return 1.0 if "survey" not in unit else 1.0000020
    if "met" in unit:
        return 3.280839895
    raise ValueError(f"Unsupported CRS unit: {unit}. Use a projected CRS in feet or metres.")


def sqft_to_acres(sqft):
    return sqft / 43560.0


def area_acres(geoseries: gpd.GeoSeries) -> "gpd.pd.Series":
    k = crs_unit_to_feet(CRS(geoseries.crs))
    return sqft_to_acres(geoseries.area * k * k)


def length_feet(geoseries: gpd.GeoSeries):
    k = crs_unit_to_feet(CRS(geoseries.crs))
    return geoseries.length * k


def cache_dir(cfg: dict) -> Path:
    return cfg["_root"] / cfg.get("cache_dir", "data/cache")


def cache_path(cfg: dict, spec: dict) -> Path:
    """Local file a remote source is cached to (vectors -> .gpkg, rasters -> .tif)."""
    ext = ".tif" if spec.get("source") in ("arcgis_image",) or spec.get("kind") == "raster" else ".gpkg"
    return cache_dir(cfg) / f"{spec['name']}{ext}"


def layer_path(spec: dict, cfg: dict) -> Path:
    """Resolve a config entry to a local file: its `path` for files, the cache for remote sources."""
    if spec.get("source", "file") != "file":
        p = cache_path(cfg, spec)
        if not p.exists():
            sys.exit(f"{spec['name']} is a remote source but is not cached yet. Run scripts/00_fetch.py first.")
        return p
    return cfg["_root"] / spec["path"]


def read_layer(spec: dict, cfg: dict) -> gpd.GeoDataFrame:
    """Read a vector layer described by a config entry and reproject to the project CRS."""
    path = layer_path(spec, cfg)
    if not path.exists():
        sys.exit(f"Layer not found: {path}")
    kwargs = {}
    if spec.get("layer") and spec.get("source", "file") == "file":
        kwargs["layer"] = spec["layer"]
    gdf = gpd.read_file(path, **kwargs)
    if gdf.crs is None:
        sys.exit(f"{path} has no CRS defined. Define it in ArcGIS Pro before exporting.")
    gdf = gdf.to_crs(cfg["crs"])
    # Repair invalid geometries (bow-ties, self-touching rings) so overlays do not fail.
    gdf["geometry"] = gdf.geometry.make_valid()
    return gdf


def read_parcels(cfg: dict) -> gpd.GeoDataFrame:
    spec = dict(cfg["parcels"], name="parcels")
    gdf = read_layer(spec, cfg)
    idf = spec.get("id_field")
    if idf not in gdf.columns:
        sys.exit(f"id_field '{idf}' not in parcel layer. Columns: {list(gdf.columns)}")
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    keep = spec.get("keep_fields")
    if keep:  # trim assessment exports with 100+ columns to what we use
        keep = [c for c in keep if c in gdf.columns]
        gdf = gdf[keep + ["geometry"]]
    return gdf


def property_path(cfg: dict) -> Path:
    return cfg["_out"] / "property.gpkg"


def write_md(path: Path, text: str):
    path.write_text(text)
    print(f"wrote {path.relative_to(ROOT)}")


def find_spec(cfg: dict, role: str, section: str = "overlays"):
    """First config entry in `section` with this role (or this name)."""
    for spec in cfg.get(section) or []:
        if spec.get("role") == role or spec.get("name") == role:
            return spec
    return None


def read_role(cfg: dict, role: str):
    """Read the (uncached-aware) layer for a role, or None if not configured / not cached."""
    spec = find_spec(cfg, role)
    if spec is None:
        return None
    if spec.get("source", "file") != "file" and not cache_path(cfg, spec).exists():
        return None
    return read_layer(spec, cfg)
