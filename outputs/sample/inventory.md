# Data inventory

### dem.json

- ERROR: '/home/user/property-analysis/data/cache/sample/dem.json' not recognized as being in a supported file format.; It might help to specify the correct driver explicitly by prefixing the file path with '<DRIVER>:', e.g. 'CSV:path'.

### dem.tif

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
- Fields: GFID (str), OBJECTID (int64), DFIRM_ID (str), VERSION_ID (str), FLD_AR_ID (str), STUDY_TYP (str), FLD_ZONE (str), ZONE_SUBTY (str), SFHA_TF (str), STATIC_BFE (int64), V_DATUM (object), DEPTH (int64), LEN_UNIT (object), VELOCITY (int64), VEL_UNIT (object), AR_REVERT (object), AR_SUBTRV (object), BFE_REVERT (int64), DEP_REVERT (int64), DUAL_ZONE (object), SOURCE_CIT (str), GlobalID (str), SHAPE.STArea() (float64), SHAPE.STLength() (float64)

### fema_flood.json

- ERROR: '/home/user/property-analysis/data/cache/sample/fema_flood.json' not recognized as being in a supported file format.; It might help to specify the correct driver explicitly by prefixing the file path with '<DRIVER>:', e.g. 'CSV:path'.

### nhd_flowlines.gpkg :: nhd_flowlines

- CRS: `EPSG:4326`
- Geometry: LineString
- Features: 4
- Bounds: -75.7, 40.2 to -75.7, 40.2
- Fields: gnis_name (str), fcode (int64), ftype (int64)

### nhd_flowlines.json

- ERROR: '/home/user/property-analysis/data/cache/sample/nhd_flowlines.json' not recognized as being in a supported file format.; It might help to specify the correct driver explicitly by prefixing the file path with '<DRIVER>:', e.g. 'CSV:path'.

### nwi_wetlands.gpkg :: nwi_wetlands

- CRS: `EPSG:4326`
- Geometry: Polygon
- Features: 12
- Bounds: -75.7, 40.1 to -75.5, 40.2
- Fields: OBJECTID (int64), Shape_Length (float64), Shape_Area (float64), GlobalID (str), ATTRIBUTE (str), WETLAND_TYPE (str), QAQC_CODE (object), ACRES (float64)

### nwi_wetlands.json

- ERROR: '/home/user/property-analysis/data/cache/sample/nwi_wetlands.json' not recognized as being in a supported file format.; It might help to specify the correct driver explicitly by prefixing the file path with '<DRIVER>:', e.g. 'CSV:path'.

### roads.gpkg :: roads

- CRS: `EPSG:4326`
- Geometry: LineString
- Features: 4
- Bounds: -75.7, 40.1 to -75.7, 40.2
- Fields: BASENAME (str), MTFCC (str), NAME (str), OBJECTID (int64), OID (str), PREDIR (object), PREDIRABRV (object), PREQUAL (float64), PREQUALABRV (str), PRETYP (object), PRETYPEABRV (object), RTTYP (str), SUFDIR (object), SUFDIRABRV (object), SUFQUAL (object), SUFQUALABRV (object), SUFTYP (int64), SUFTYPEABRV (str)

### roads.json

- ERROR: '/home/user/property-analysis/data/cache/sample/roads.json' not recognized as being in a supported file format.; It might help to specify the correct driver explicitly by prefixing the file path with '<DRIVER>:', e.g. 'CSV:path'.

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
