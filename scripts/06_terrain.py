"""Terrain from the DEM named "dem" in config: slope, aspect, hillshade, slope classes by acres,
per parcel and for the whole property. Skips quietly if no DEM is configured."""
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from rasterio.mask import mask

sys.path.insert(0, str(Path(__file__).parent))
from _common import crs_unit_to_feet, layer_path, load_config, property_path, write_md  # noqa: E402
from pyproj import CRS  # noqa: E402

SLOPE_CLASSES = [(0, 3, "0-3% (flat)"), (3, 8, "3-8% (gentle)"), (8, 15, "8-15% (moderate)"),
                 (15, 25, "15-25% (steep)"), (25, 1e9, ">25% (very steep)")]


def main():
    cfg = load_config()
    dem_spec = next((r for r in (cfg.get("rasters") or []) if r["name"] == "dem"), None)
    if not dem_spec:
        print("no DEM configured (rasters: - name: dem); skipping terrain")
        return
    dem_path = layer_path(dict(dem_spec, kind="raster"), cfg)
    parcels = gpd.read_file(property_path(cfg), layer="parcels")
    boundary = gpd.read_file(property_path(cfg), layer="property_boundary")
    idf = cfg["parcels"]["id_field"]
    out = cfg["_out"]

    with rasterio.open(dem_path) as src:
        if CRS(src.crs) != CRS(cfg["crs"]):
            sys.exit(f"DEM CRS {src.crs} differs from project CRS {cfg['crs']}; reproject it first.")
        z = src.read(1).astype("float64")
        nodata = src.nodata
        if nodata is not None:
            z[z == nodata] = np.nan
        z[z < -1000] = np.nan
        transform, profile = src.transform, src.profile
        xres, yres = src.res
        # Elevation units: 3DEP is metres; convert to CRS horizontal units for slope.
        z_units = dem_spec.get("z_units", "m")
        k_ft = crs_unit_to_feet(CRS(cfg["crs"]))              # crs unit -> ft
        z_to_crs = (3.280839895 / k_ft) if z_units == "m" else (1.0 / k_ft)
        zc = z * z_to_crs
        dzdx = np.gradient(zc, xres, axis=1)
        dzdy = -np.gradient(zc, yres, axis=0)
        slope_pct = np.hypot(dzdx, dzdy) * 100
        slope_deg = np.degrees(np.arctan(np.hypot(dzdx, dzdy)))
        aspect = (np.degrees(np.arctan2(dzdx, dzdy)) + 360) % 360
        az, alt = np.radians(315), np.radians(45)
        hs = (np.sin(alt) * np.cos(np.radians(slope_deg)) +
              np.cos(alt) * np.sin(np.radians(slope_deg)) * np.cos(az - np.radians(aspect)))
        hillshade = np.clip(hs * 255, 0, 255)

    profile.update(dtype="float32", count=1, nodata=-9999, compress="lzw")
    for name, arr in [("slope_pct", slope_pct), ("aspect_deg", aspect), ("hillshade", hillshade)]:
        with rasterio.open(out / f"{name}.tif", "w", **profile) as dst:
            dst.write(np.where(np.isnan(arr), -9999, arr).astype("float32"), 1)
        print(f"wrote {name}.tif")

    # Slope classes by parcel and for the whole property
    cell_acres = xres * yres * k_ft * k_ft / 43560.0
    pid = rasterize(((g, i + 1) for i, g in enumerate(parcels.geometry)), out_shape=slope_pct.shape,
                    transform=transform, fill=0, dtype="int32")
    rows = []
    for i, r in parcels.iterrows():
        m = (pid == i + 1) & ~np.isnan(slope_pct)
        for lo, hi, label in SLOPE_CLASSES:
            n = int(((slope_pct >= lo) & (slope_pct < hi) & m).sum())
            rows.append({idf: r[idf], "slope_class": label, "acres": round(n * cell_acres, 3)})
        rows_z = z[m]
    by_parcel = pd.DataFrame(rows)
    by_class = by_parcel.groupby("slope_class", sort=False)["acres"].sum().reset_index()
    by_class["pct"] = (100 * by_class["acres"] / by_class["acres"].sum()).round(1)
    inside = (pid > 0) & ~np.isnan(z)
    zin = z[inside]
    stats = {"min": float(np.nanmin(zin)), "max": float(np.nanmax(zin)), "mean": float(np.nanmean(zin))}
    by_parcel.to_csv(out / "slope_by_parcel.csv", index=False)
    by_class.to_csv(out / "slope_by_class.csv", index=False)

    unit = "m" if z_units == "m" else "ft"
    md = ["# Terrain", "",
          f"- DEM: `{dem_path.name}` at {xres:.1f} x {yres:.1f} CRS units per cell",
          f"- Elevation within property: {stats['min']:.1f} to {stats['max']:.1f} {unit} "
          f"(mean {stats['mean']:.1f} {unit}, relief {stats['max'] - stats['min']:.1f} {unit})",
          f"- Mean slope within property: {np.nanmean(slope_pct[inside]):.1f}%", "",
          "## Slope classes (whole property)", "", by_class.to_markdown(index=False), "",
          "## Slope classes by parcel", "",
          by_parcel.pivot(index=idf, columns="slope_class", values="acres")[[c[2] for c in SLOPE_CLASSES]]
          .reset_index().to_markdown(index=False), "",
          "Rasters written: slope_pct.tif, aspect_deg.tif, hillshade.tif (open in ArcGIS Pro).", ""]
    write_md(out / "terrain.md", "\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
