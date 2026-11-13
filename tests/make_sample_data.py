"""Build a small synthetic dataset (4 parcels with one overlap and one gap, plus a wetlands
and a zoning layer) so the pipeline can be exercised before real data is added.
Writes data/sample/sample.gpkg. Run: python3 tests/make_sample_data.py
"""
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Polygon, box

ROOT = Path(__file__).resolve().parents[1]
CRS = "EPSG:2272"  # PA South, US ft. Site in rural Chester County so public layers have content.
X0, Y0 = 2_544_000, 311_500

parcels = gpd.GeoDataFrame({
    "PARCEL_ID": ["101-A", "101-B", "102", "103"],
    "OWNER": ["Smith", "Smith", "Jones Trust", "Jones Trust"],
    "DEED_ACRES": [5.0, 3.2, 4.1, 2.9],
    "geometry": [
        box(X0, Y0, X0 + 500, Y0 + 440),                       # 5.05 ac
        box(X0 + 495, Y0, X0 + 800, Y0 + 440),                 # overlaps 101-A by 5 ft strip
        Polygon([(X0, Y0 + 440), (X0 + 420, Y0 + 440), (X0 + 420, Y0 + 860), (X0, Y0 + 860)]),
        Polygon([(X0 + 430, Y0 + 440), (X0 + 800, Y0 + 440), (X0 + 800, Y0 + 780), (X0 + 430, Y0 + 780)]),
    ]}, crs=CRS)
# 10 ft gap between 102 and 103 (x 420..430) is intentional; it is an exterior notch, not a hole.
# Make an interior gap: punch a hole shared by 102/103 boundary by shifting 103 slightly.
parcels.loc[3, "geometry"] = Polygon([(X0 + 420, Y0 + 440), (X0 + 800, Y0 + 440), (X0 + 800, Y0 + 780),
                                      (X0 + 420, Y0 + 780), (X0 + 420, Y0 + 620), (X0 + 440, Y0 + 620),
                                      (X0 + 440, Y0 + 600), (X0 + 420, Y0 + 600)])

wetlands = gpd.GeoDataFrame({
    "WETLAND_TYPE": ["PFO", "PEM"],
    "geometry": [box(X0 - 50, Y0 + 300, X0 + 300, Y0 + 520), box(X0 + 600, Y0 + 600, X0 + 900, Y0 + 900)],
}, crs=CRS)
zoning = gpd.GeoDataFrame({
    "ZONE": ["R-1", "AG"],
    "geometry": [box(X0 - 200, Y0 - 200, X0 + 450, Y0 + 1000), box(X0 + 450, Y0 - 200, X0 + 1000, Y0 + 1000)],
}, crs=CRS)

out = ROOT / "data" / "sample" / "sample.gpkg"
out.parent.mkdir(parents=True, exist_ok=True)
if out.exists():
    out.unlink()
parcels.to_file(out, layer="parcels", driver="GPKG")
wetlands.to_file(out, layer="wetlands", driver="GPKG")
zoning.to_file(out, layer="zoning", driver="GPKG")
print(f"wrote {out}")
