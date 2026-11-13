"""Per-parcel and total measurements: acreage, perimeter, comparison with recorded acreage."""
import sys
from pathlib import Path

import geopandas as gpd

sys.path.insert(0, str(Path(__file__).parent))
from _common import area_acres, length_feet, load_config, property_path, write_md  # noqa: E402


def main():
    cfg = load_config()
    idf = cfg["parcels"]["id_field"]
    acres_field = cfg["parcels"].get("acres_field")
    parcels = gpd.read_file(property_path(cfg), layer="parcels")
    boundary = gpd.read_file(property_path(cfg), layer="property_boundary")

    t = parcels[[idf]].copy()
    t["acres_computed"] = area_acres(parcels.geometry).round(3)
    t["sqft_computed"] = (t["acres_computed"] * 43560).round(0)
    t["perimeter_ft"] = length_feet(parcels.geometry).round(1)
    if acres_field and acres_field in parcels.columns:
        t["acres_recorded"] = parcels[acres_field].astype(float).round(3)
        t["difference"] = (t["acres_computed"] - t["acres_recorded"]).round(3)
        t["difference_pct"] = (100 * t["difference"] / t["acres_recorded"]).round(1)
    t["share_of_property_pct"] = (100 * t["acres_computed"] / t["acres_computed"].sum()).round(1)
    t = t.sort_values(idf)

    total_acres = round(float(area_acres(boundary.geometry).iloc[0]), 3)
    total_perim = round(float(length_feet(boundary.geometry).iloc[0]), 1)
    csv = cfg["_out"] / "parcel_measurements.csv"
    t.to_csv(csv, index=False)
    print(f"wrote {csv.relative_to(cfg['_root'])}")

    md = ["# Measurements", "",
          f"- Total property area (dissolved): **{total_acres} acres** ({total_acres * 43560:,.0f} sq ft)",
          f"- Sum of parcel areas: {t['acres_computed'].sum():.3f} acres "
          "(differs from dissolved total if parcels overlap)",
          f"- Outer perimeter of property: {total_perim:,.1f} ft", "",
          "## Per parcel", "", t.to_markdown(index=False), ""]
    write_md(cfg["_out"] / "measurements.md", "\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
