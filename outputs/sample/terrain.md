# Terrain

- DEM: `dem.tif` at 10.0 x 10.0 CRS units per cell
- Elevation within property: 79.4 to 83.5 m (mean 81.5 m, relief 4.1 m)
- Mean slope within property: 4.1%

## Slope classes (whole property)

| slope_class       |   acres |   pct |
|:------------------|--------:|------:|
| 0-3% (flat)       |   9.183 |  60.9 |
| 3-8% (gentle)     |   3.939 |  26.1 |
| 8-15% (moderate)  |   1.291 |   8.6 |
| 15-25% (steep)    |   0.582 |   3.9 |
| >25% (very steep) |   0.094 |   0.6 |

## Slope classes by parcel

| PARCEL_ID   |   0-3% (flat) |   15-25% (steep) |   3-8% (gentle) |   8-15% (moderate) |   >25% (very steep) |
|:------------|--------------:|-----------------:|----------------:|-------------------:|--------------------:|
| 101-A       |         3.632 |            0.129 |           0.863 |              0.409 |               0.018 |
| 101-B       |         2.151 |            0.005 |           0.76  |              0.115 |               0     |
| 102         |         1.396 |            0.443 |           1.455 |              0.68  |               0.076 |
| 103         |         2.004 |            0.005 |           0.861 |              0.087 |               0     |

Rasters written: slope_pct.tif, aspect_deg.tif, hillshade.tif (open in ArcGIS Pro).
