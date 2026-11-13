# Data inventory

### dem_3dep.tif

- CRS: `EPSG:2272`
- Size: 180 x 186 px, 1 band(s), float32
- Resolution: 10.00 x 10.00
- Bounds: 2543500.0, 311000.0 to 2545300.0, 312860.0
- NoData: None

### fema_flood.gpkg :: fema_flood

- CRS: `EPSG:4326`
- Geometry: Polygon
- Features: 3
- Bounds: -75.9, 39.9 to -75.4, 40.2
- Fields: FLD_ZONE (str), ZONE_SUBTY (str), SFHA_TF (str), STATIC_BFE (int64)

### nhd_flowlines.gpkg :: nhd_flowlines

- CRS: `EPSG:4326`
- Geometry: LineString
- Features: 4
- Bounds: -75.7, 40.2 to -75.7, 40.2
- Fields: gnis_name (str), fcode (int64), ftype (int64)

### nwi_wetlands.gpkg :: nwi_wetlands

- CRS: `EPSG:4326`
- Geometry: Polygon
- Features: 12
- Bounds: -75.7, 40.1 to -75.5, 40.2
- Fields: ATTRIBUTE (str), WETLAND_TYPE (str)

### tiger_roads.gpkg :: tiger_roads

- CRS: `EPSG:4326`
- Geometry: LineString
- Features: 4
- Bounds: -75.7, 40.1 to -75.7, 40.2
- Fields: NAME (str), MTFCC (str)

### sample.gpkg :: parcels

- CRS: `EPSG:2272`
- Geometry: Polygon
- Features: 4
- Bounds: 2544000.0, 311500.0 to 2544800.0, 312360.0
- Fields: PARCEL_ID (str), OWNER (str), DEED_ACRES (float64)

### sample.gpkg :: wetlands

- CRS: `EPSG:2272`
- Geometry: Polygon
- Features: 2
- Bounds: 2543950.0, 311800.0 to 2544900.0, 312400.0
- Fields: WETLAND_TYPE (str)

### sample.gpkg :: zoning

- CRS: `EPSG:2272`
- Geometry: Polygon
- Features: 2
- Bounds: 2543800.0, 311300.0 to 2545000.0, 312500.0
- Fields: ZONE (str)
