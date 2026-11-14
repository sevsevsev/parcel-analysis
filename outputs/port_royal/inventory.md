# Data inventory

### fema_flood.gpkg :: fema_flood

- CRS: `EPSG:4326`
- Geometry: Polygon
- Features: 4
- Bounds: -75.3, 40.0 to -75.2, 40.1
- Fields: FLD_ZONE (str), ZONE_SUBTY (str), SFHA_TF (str), STATIC_BFE (int64)

### nhd_flowlines.gpkg :: nhd_flowlines

- CRS: `EPSG:4326`
- Geometry: 
- Features: 0
- Bounds: nan, nan to nan, nan
- Fields: 

### nhd_waterbodies.gpkg :: nhd_waterbodies

- CRS: `EPSG:4326`
- Geometry: 
- Features: 0
- Bounds: nan, nan to nan, nan
- Fields: 

### nwi_wetlands.gpkg :: nwi_wetlands

- CRS: `EPSG:4326`
- Geometry: Polygon
- Features: 1
- Bounds: -76.0, 40.0 to -75.3, 40.6
- Fields: ATTRIBUTE (str), WETLAND_TYPE (str)

### phl_buildings.gpkg :: phl_buildings

- CRS: `EPSG:4326`
- Geometry: Polygon
- Features: 32
- Bounds: -75.3, 40.0 to -75.2, 40.1
- Fields: address (str), building_name (object), approx_hgt (int64), square_ft (int64), parcel_id_num (str)

### phl_steep_slope_area.gpkg :: phl_steep_slope_area

- CRS: `EPSG:4326`
- Geometry: MultiPolygon
- Features: 1
- Bounds: -75.3, 39.9 to -75.0, 40.1
- Fields: overlay_na (str), regulation (str), code_secti (str)

### phl_streets.gpkg :: phl_streets

- CRS: `EPSG:4326`
- Geometry: LineString
- Features: 6
- Bounds: -75.3, 40.0 to -75.2, 40.1
- Fields: st_name (str), st_type (str), st_code (int64)

### phl_tree_canopy.gpkg :: phl_tree_canopy

- CRS: `EPSG:4326`
- Geometry: Polygon
- Features: 167
- Bounds: -75.3, 40.0 to -75.2, 40.1
- Fields: avg_height (int64)

### phl_zoning.gpkg :: phl_zoning

- CRS: `EPSG:4326`
- Geometry: Polygon
- Features: 5
- Bounds: -75.3, 40.0 to -75.2, 40.1
- Fields: code (str), long_code (str), zoninggroup (str), pending (str)

### phl_zoning_overlays.gpkg :: phl_zoning_overlays

- CRS: `EPSG:4326`
- Geometry: MultiPolygon
- Features: 7
- Bounds: -75.3, 39.9 to -75.0, 40.1
- Fields: overlay_name (str), overlay_symbol (str), type (str), code_section (str), code_section_link (str)

### ssurgo_soils.gpkg :: ssurgo_soils

- CRS: `EPSG:4326`
- Geometry: MultiPolygon
- Features: 10
- Bounds: -75.3, 39.9 to -75.0, 40.1
- Fields: mukey (str), musym (str), muname (str), farmlndcl (str), compname (str), comppct_r (int64), hydgrp (str), drainagecl (str), hydricrating (str), slope_r (float64), runoff (str), flood_freq (str), resdept_cm (float64), wet_depth_cm (float64)

### PortRoyalParcel.shp

- CRS: `EPSG:3857`
- Geometry: Polygon
- Features: 1
- Bounds: -8377151.6, 4872921.1 to -8376881.7, 4873192.0
- Fields: PARCELID (int64), TENCODE (str), ADDRESS (str), OWNER1 (str), OWNER2 (str), BLDG_DESC (str), IMPERV_ARE (int64), BC_LANDUSE (str), BC_TYPE (str), IMP_ROOF (float64), IMP_GROUND (float64), IMP_TOTAL (float64), NATURAL_GR (float64), TOTAL_GROU (float64), COUNCIL_DI (str), PCPC_DISTR (str), PUBLIC_PRI (str), PROGRAM (str), OWNER_CATE (str), Shape__Are (float64), Shape__Len (float64)
