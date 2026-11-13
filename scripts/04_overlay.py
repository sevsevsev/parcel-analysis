"""Overlay each constraint layer from config on the property and summarise acres by class."""
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from _common import area_acres, cache_path, load_config, property_path, read_layer, write_md  # noqa: E402


def main():
    cfg = load_config()
    overlays = cfg.get("overlays") or []
    idf = cfg["parcels"]["id_field"]
    parcels = gpd.read_file(property_path(cfg), layer="parcels")
    boundary = gpd.read_file(property_path(cfg), layer="property_boundary")
    total_acres = float(area_acres(boundary.geometry).iloc[0])

    md = ["# Overlay analysis", "", f"Property area: {total_acres:.3f} acres", ""]
    if not overlays:
        md.append("_No overlay layers configured. Add entries under `overlays:` in config.yaml._")
    out_gpkg = cfg["_out"] / "overlays.gpkg"
    if out_gpkg.exists():
        out_gpkg.unlink()

    for spec in overlays:
        name, cls = spec["name"], spec.get("class_field")
        if spec.get("source", "file") != "file" and not cache_path(cfg, spec).exists():
            md += [f"## {name}", "", "_Skipped: remote layer not cached (fetch failed). See sources.md._", ""]
            print(f"skipping {name}: not cached")
            continue
        layer = read_layer(spec, cfg)
        # Drop server-side computed fields (e.g. "SHAPE.STArea()") and any field that would clash
        # with our own calc_acres column (GeoPackage field names are case-insensitive).
        layer = layer[[c for c in layer.columns if "(" not in c and c.lower() != "calc_acres"]]
        if len(layer) == 0:
            md += [f"## {name}", "", "_No features of this layer intersect the area of interest._", ""]
            continue
        if layer.geom_type.isin(["Polygon", "MultiPolygon"]).all():
            # Totals use the dissolved boundary so overlapping parcels are not double counted;
            # the per-parcel table uses the parcels themselves.
            on_prop = gpd.overlay(boundary[["geometry"]], layer, how="intersection", keep_geom_type=True)
            on_prop["calc_acres"] = area_acres(on_prop.geometry)
            on_prop.to_file(out_gpkg, layer=name, driver="GPKG")
            clipped = gpd.overlay(parcels[[idf, "geometry"]], layer, how="intersection", keep_geom_type=True)
            clipped["calc_acres"] = area_acres(clipped.geometry)
            if cls and cls in on_prop.columns:
                by_class = on_prop.groupby(cls)["calc_acres"].sum().reset_index().rename(columns={"calc_acres": "acres"})
            else:
                by_class = pd.DataFrame({"class": ["(all)"], "acres": [on_prop["calc_acres"].sum()]})
                cls = "class"
            by_class["pct_of_property"] = (100 * by_class["acres"] / total_acres).round(1)
            by_class["acres"] = by_class["acres"].round(3)
            by_parcel = clipped.groupby([idf] + ([cls] if cls in clipped.columns else []))["calc_acres"] \
                .sum().round(3).reset_index().rename(columns={"calc_acres": "acres"})
            by_class.to_csv(cfg["_out"] / f"overlay_{name}_by_class.csv", index=False)
            by_parcel.to_csv(cfg["_out"] / f"overlay_{name}_by_parcel.csv", index=False)
            covered = on_prop["calc_acres"].sum()
            md += [f"## {name}", "",
                   f"- Area of property covered: {covered:.3f} acres ({100 * covered / total_acres:.1f}%)",
                   f"- Area not covered: {total_acres - covered:.3f} acres", "",
                   "### By class", "", by_class.to_markdown(index=False), "",
                   "### By parcel", "", by_parcel.to_markdown(index=False), ""]
        else:
            # Lines / points: report what intersects, with length inside the property for lines.
            clipped = gpd.clip(layer, boundary)
            clipped.to_file(out_gpkg, layer=name, driver="GPKG")
            md += [f"## {name}", "", f"- Features intersecting property: {len(clipped)}"]
            if clipped.geom_type.isin(["LineString", "MultiLineString"]).any():
                from _common import length_feet
                md.append(f"- Total length inside property: {length_feet(clipped.geometry).sum():,.1f} ft")
            md.append("")
    write_md(cfg["_out"] / "overlays.md", "\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
