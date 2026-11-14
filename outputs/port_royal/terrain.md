# Terrain

- DEM: `dem_3dep.tif` at 5.0 x 5.0 CRS units per cell
- Elevation within property: 48.8 to 75.9 m (mean 63.1 m, relief 27.0 m)
- Mean slope within property: 20.0%

## Slope classes (whole property)

| slope_class       |   acres |   pct |
|:------------------|--------:|------:|
| 0-3% (flat)       |   0.045 |   1.1 |
| 3-8% (gentle)     |   0.16  |   4   |
| 8-15% (moderate)  |   0.89  |  22.3 |
| 15-25% (steep)    |   2.044 |  51.2 |
| >25% (very steep) |   0.856 |  21.4 |

## Slope classes by parcel

|   PARCELID |   0-3% (flat) |   3-8% (gentle) |   8-15% (moderate) |   15-25% (steep) |   >25% (very steep) |
|-----------:|--------------:|----------------:|-------------------:|-----------------:|--------------------:|
|     505727 |         0.045 |            0.16 |               0.89 |            2.044 |               0.856 |

Rasters written: slope_pct.tif, aspect_deg.tif, hillshade.tif (open in ArcGIS Pro).
