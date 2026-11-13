# Terrain

- DEM: `dem_3dep.tif` at 5.0 x 5.0 CRS units per cell
- Elevation within property: 62.6 to 116.4 m (mean 92.7 m, relief 53.8 m)
- Mean slope within property: 20.3%

## Slope classes (whole property)

| slope_class       |   acres |   pct |
|:------------------|--------:|------:|
| 0-3% (flat)       |   0.684 |   3.6 |
| 3-8% (gentle)     |   2.689 |  14.2 |
| 8-15% (moderate)  |   2.649 |  13.9 |
| 15-25% (steep)    |   6.474 |  34.1 |
| >25% (very steep) |   6.505 |  34.2 |

## Slope classes by parcel

|       PARCEL |   0-3% (flat) |   3-8% (gentle) |   8-15% (moderate) |   15-25% (steep) |   >25% (very steep) |
|-------------:|--------------:|----------------:|-------------------:|-----------------:|--------------------:|
| 650000454003 |         0.032 |           0.091 |              0.412 |            1.465 |               1.286 |
| 650000457009 |         0.018 |           0.091 |              0.166 |            0.614 |               1.144 |
| 650000463003 |         0.001 |           0.01  |              0.319 |            2.507 |               2.348 |
| 650000463012 |         0.001 |           0.036 |              0.162 |            1.354 |               1.713 |
| 650005329006 |         0.21  |           0.819 |              0.144 |            0.004 |               0     |
| 650005332003 |         0.196 |           0.624 |              0.272 |            0.036 |               0.013 |
| 650005338006 |         0.226 |           1.018 |              1.174 |            0.494 |               0.001 |

Rasters written: slope_pct.tif, aspect_deg.tif, hillshade.tif (open in ArcGIS Pro).
