"""Parcel QA and property assembly.

Checks: invalid geometries, duplicate IDs, overlaps between parcels, interior gaps.
Writes outputs/property.gpkg with layers: parcels, property_boundary, overlaps, gaps
and outputs/qa_report.md.
"""
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).parent))
from _common import (area_acres, crs_unit_to_feet, layer_path, load_config,  # noqa: E402
                     property_path, read_parcels, write_md)
from pyproj import CRS  # noqa: E402


def find_overlaps(parcels: gpd.GeoDataFrame, idf: str, tol_sqft: float) -> gpd.GeoDataFrame:
    k = crs_unit_to_feet(CRS(parcels.crs))
    tol = tol_sqft / (k * k)
    rows = []
    geoms = list(parcels.geometry)
    ids = list(parcels[idf])
    for i in range(len(geoms)):
        for j in range(i + 1, len(geoms)):
            if geoms[i].intersects(geoms[j]):
                inter = geoms[i].intersection(geoms[j])
                if inter.area > tol:
                    rows.append({"parcel_a": ids[i], "parcel_b": ids[j], "geometry": inter})
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=parcels.crs) if rows else \
        gpd.GeoDataFrame(columns=["parcel_a", "parcel_b", "geometry"], geometry="geometry", crs=parcels.crs)


def find_gaps(dissolved, crs, tol_sqft: float) -> gpd.GeoDataFrame:
    """Interior rings of the dissolved property are gaps between parcels."""
    k = crs_unit_to_feet(CRS(crs))
    tol = tol_sqft / (k * k)
    polys = list(dissolved.geoms) if isinstance(dissolved, MultiPolygon) else [dissolved]
    holes = []
    for p in polys:
        for ring in p.interiors:
            h = Polygon(ring)
            if h.area > tol:
                holes.append({"geometry": h})
    return gpd.GeoDataFrame(holes, geometry="geometry", crs=crs) if holes else \
        gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs=crs)


def main():
    cfg = load_config()
    idf = cfg["parcels"]["id_field"]
    parcels = read_parcels(cfg)
    qa = cfg.get("qa", {})

    issues = []
    dup = parcels[idf][parcels[idf].duplicated(keep=False)]
    if len(dup):
        issues.append(f"Duplicate parcel IDs: {sorted(set(dup))}")
    pspec = dict(cfg["parcels"], name="parcels")
    raw = gpd.read_file(layer_path(pspec, cfg),
                        **({"layer": pspec["layer"]} if pspec.get("layer") and pspec.get("source", "file") == "file" else {}))
    n_invalid = int((~raw.geometry.is_valid).sum())
    if n_invalid:
        issues.append(f"{n_invalid} geometries were invalid in the source and were repaired with make_valid().")
    multi = parcels[parcels.geom_type == "MultiPolygon"]
    if len(multi):
        issues.append(f"{len(multi)} parcels are multipart: {list(multi[idf])}")

    overlaps = find_overlaps(parcels, idf, qa.get("overlap_tolerance_sqft", 10))
    dissolved = unary_union(parcels.geometry)
    gaps = find_gaps(dissolved, parcels.crs, qa.get("gap_tolerance_sqft", 10))
    n_parts = len(dissolved.geoms) if isinstance(dissolved, MultiPolygon) else 1

    boundary = gpd.GeoDataFrame({"name": ["property"], "geometry": [dissolved]}, crs=parcels.crs)
    boundary["acres"] = area_acres(boundary.geometry).round(3)

    out = property_path(cfg)
    if out.exists():
        out.unlink()
    parcels.to_file(out, layer="parcels", driver="GPKG")
    boundary.to_file(out, layer="property_boundary", driver="GPKG")
    overlaps.to_file(out, layer="overlaps", driver="GPKG")
    gaps.to_file(out, layer="gaps", driver="GPKG")
    print(f"wrote {out.relative_to(cfg['_root'])}")

    lines = ["# Parcel QA report", "",
             f"- Parcels: {len(parcels)}",
             f"- Project CRS: `{parcels.crs.to_string()}`",
             f"- Dissolved property: {n_parts} contiguous part(s), {boundary['acres'].iloc[0]:.3f} acres",
             f"- Overlaps found: {len(overlaps)}",
             f"- Interior gaps found: {len(gaps)}", ""]
    if issues:
        lines += ["## Issues", ""] + [f"- {i}" for i in issues] + [""]
    if len(overlaps):
        overlaps["acres"] = area_acres(overlaps.geometry)
        overlaps["sqft"] = overlaps["acres"] * 43560
        lines += ["## Overlaps", "", overlaps[["parcel_a", "parcel_b", "sqft"]].round(1)
                  .to_markdown(index=False), ""]
    if len(gaps):
        gaps["sqft"] = area_acres(gaps.geometry) * 43560
        lines += ["## Gaps", "", gaps[["sqft"]].round(1).to_markdown(index=False), ""]
    if n_parts > 1:
        lines += [f"**Note:** the parcels do not form one contiguous property ({n_parts} parts). "
                  "Check for missing parcels or slivers between them.", ""]
    if not issues and not len(overlaps) and not len(gaps) and n_parts == 1:
        lines += ["No problems found. Parcels form a single clean polygon.", ""]
    write_md(cfg["_out"] / "qa_report.md", "\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
