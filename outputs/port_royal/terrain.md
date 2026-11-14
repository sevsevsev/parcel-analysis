# Terrain

- DEM: `dem_3dep.tif` at 5.0 x 5.0 CRS units per cell
- Elevation within property: 48.7 to 75.8 m (mean 63.1 m, relief 27.2 m)
- Mean slope within property: 20.0%

## Slope classes (whole property)

| slope_class       |   acres |   pct |
|:------------------|--------:|------:|
| 0-3% (flat)       |   0.041 |   1   |
| 3-8% (gentle)     |   0.157 |   3.9 |
| 8-15% (moderate)  |   0.897 |  22.5 |
| 15-25% (steep)    |   2.041 |  51.1 |
| >25% (very steep) |   0.856 |  21.4 |

## Slope classes by parcel

|   PARCELID |   0-3% (flat) |   3-8% (gentle) |   8-15% (moderate) |   15-25% (steep) |   >25% (very steep) |
|-----------:|--------------:|----------------:|-------------------:|-----------------:|--------------------:|
|     505727 |         0.041 |           0.157 |              0.897 |            2.041 |               0.856 |

Rasters written: slope_pct.tif, aspect_deg.tif, hillshade.tif (open in ArcGIS Pro).
