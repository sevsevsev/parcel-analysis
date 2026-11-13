"""Inventory every spatial file under data/: layers, CRS, geometry type, feature count, fields.

Run this first after adding data so we know what we are working with.
"""
import sys
from pathlib import Path

import geopandas as gpd
import pyogrio
import rasterio

sys.path.insert(0, str(Path(__file__).parent))
from _common import load_config, write_md  # noqa: E402

VECTOR_EXT = {".gpkg", ".shp", ".geojson", ".kml", ".gdb"}  # plain .json is cache metadata
RASTER_EXT = {".tif", ".tiff", ".img", ".vrt"}


def describe_vector(path: Path, layer: str | None) -> str:
    gdf = gpd.read_file(path, layer=layer) if layer else gpd.read_file(path)
    b = gdf.total_bounds
    name = f"{path.name}" + (f" :: {layer}" if layer else "")
    crs = gdf.crs.to_string() if gdf.crs else "**NO CRS**"
    geoms = ", ".join(sorted(gdf.geom_type.dropna().unique()))
    fields = ", ".join(f"{c} ({gdf[c].dtype})" for c in gdf.columns if c != "geometry")
    return (
        f"### {name}\n\n"
        f"- CRS: `{crs}`\n- Geometry: {geoms}\n- Features: {len(gdf)}\n"
        f"- Bounds: {b[0]:.1f}, {b[1]:.1f} to {b[2]:.1f}, {b[3]:.1f}\n"
        f"- Fields: {fields}\n"
    )


def describe_raster(path: Path) -> str:
    with rasterio.open(path) as src:
        crs = src.crs.to_string() if src.crs else "**NO CRS**"
        return (
            f"### {path.name}\n\n- CRS: `{crs}`\n- Size: {src.width} x {src.height} px, "
            f"{src.count} band(s), {src.dtypes[0]}\n- Resolution: {src.res[0]:.2f} x {src.res[1]:.2f}\n"
            f"- Bounds: {src.bounds.left:.1f}, {src.bounds.bottom:.1f} to "
            f"{src.bounds.right:.1f}, {src.bounds.top:.1f}\n- NoData: {src.nodata}\n"
        )


def main():
    cfg = load_config()
    # Only this listing's files: its raw inputs (the parcel file's folder) and its cache.
    from _common import cache_dir
    dirs = [cache_dir(cfg)]
    if cfg["parcels"].get("source", "file") == "file":
        dirs.append((cfg["_root"] / cfg["parcels"]["path"]).parent)
    for spec in cfg.get("overlays") or []:
        if spec.get("source", "file") == "file":
            dirs.append((cfg["_root"] / spec["path"]).parent)
    paths = sorted({p for d in dirs if d.exists() for p in d.rglob("*")})
    sections = []
    for path in paths:
        if path.suffix.lower() in VECTOR_EXT and path.is_file() or path.suffix.lower() == ".gdb":
            try:
                if path.suffix.lower() in {".gpkg", ".gdb"}:
                    for layer, _ in pyogrio.list_layers(path):
                        sections.append(describe_vector(path, layer))
                else:
                    sections.append(describe_vector(path, None))
            except Exception as e:  # keep going; report the problem
                sections.append(f"### {path.name}\n\n- ERROR: {e}\n")
        elif path.suffix.lower() in RASTER_EXT and path.is_file():
            try:
                sections.append(describe_raster(path))
            except Exception as e:
                sections.append(f"### {path.name}\n\n- ERROR: {e}\n")
    body = "# Data inventory\n\n" + ("\n".join(sections) if sections else "_No spatial files found under data/._\n")
    write_md(cfg["_out"] / "inventory.md", body)
    print(body)


if __name__ == "__main__":
    main()
