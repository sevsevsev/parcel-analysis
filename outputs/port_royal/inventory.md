# Data inventory

### dem_3dep.tif

- CRS: `EPSG:2272`
- Size: 338 x 334 px, 1 band(s), float32
- Resolution: 5.00 x 5.00
- Bounds: 2666893.1, 269741.4 to 2668583.1, 271411.4
- NoData: None

### dep_streams_ch93.gpkg :: dep_streams_ch93

- CRS: `EPSG:4326`
- Geometry: 
- Features: 0
- Bounds: nan, nan to nan, nan
- Fields: 

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

### nrhp_districts.gpkg :: nrhp_districts

- CRS: `EPSG:4326`
- Geometry: Polygon
- Features: 2
- Bounds: -75.3, 40.0 to -75.2, 40.1
- Fields: RESNAME (str), ResType (str), NRIS_Refnum (str), CertDate (str), Is_NHL (object), NARA_URL (str)

### nwi_wetlands.gpkg :: nwi_wetlands

- CRS: `EPSG:4326`
- Geometry: Polygon
- Features: 1
- Bounds: -76.0, 40.0 to -75.3, 40.6
- Fields: ATTRIBUTE (str), WETLAND_TYPE (str)

### pa_conservation_easements.gpkg :: pa_conservation_easements

- CRS: `EPSG:4326`
- Geometry: Polygon
- Features: 1
- Bounds: -75.3, 40.0 to -75.2, 40.1
- Fields: sitename (str), esmthldr (str), eholdtype (str), purpose (str), pub_access (str), duration (str), est_year (int64), acres_gis (float64)

### penndot_traffic.gpkg :: penndot_traffic

- CRS: `EPSG:4326`
- Geometry: MultiLineString
- Features: 3
- Bounds: -75.3, 40.0 to -75.2, 40.1
- Fields: ST_RT_NO (str), CUR_AADT (int64), ADTT_CUR (int64), TRK_PCT (int64), BASE_YR_CL (int64)

### phl_buildings.gpkg :: phl_buildings

- CRS: `EPSG:4326`
- Geometry: Polygon
- Features: 32
- Bounds: -75.3, 40.0 to -75.2, 40.1
- Fields: address (str), building_name (object), approx_hgt (int64), square_ft (int64), parcel_id_num (str)

### phl_historic_local.gpkg :: phl_historic_local

- CRS: `EPSG:4326`
- Geometry: MultiPolygon
- Features: 1
- Bounds: -75.3, 39.9 to -75.1, 40.1
- Fields: name (str), designated (int64)

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
- Fields: code (str), long_code (str), zoninggroup (str), pending (str), code_description (str), MinLotArea (str), MaxHeight (str), MinPercent (str), description (str)

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
- Fields: mukey (str), musym (str), muname (str), farmlndcl (str), compname (str), comppct_r (int64), hydgrp (str), drainagecl (str), hydricrating (str), slope_r (float64), runoff (str), flood_freq (str), resdept_cm (float64), wet_depth_cm (float64), septic_rating (str), basement_rating (str), frost_free_days (int64)

### PortRoyalParcel.shp

- CRS: `EPSG:3857`
- Geometry: Polygon
- Features: 1
- Bounds: -8377151.6, 4872921.1 to -8376881.7, 4873192.0
- Fields: PARCELID (int64), TENCODE (str), ADDRESS (str), OWNER1 (str), OWNER2 (str), BLDG_DESC (str), IMPERV_ARE (int64), BC_LANDUSE (str), BC_TYPE (str), IMP_ROOF (float64), IMP_GROUND (float64), IMP_TOTAL (float64), NATURAL_GR (float64), TOTAL_GROU (float64), COUNCIL_DI (str), PCPC_DISTR (str), PUBLIC_PRI (str), PROGRAM (str), OWNER_CATE (str), Shape__Are (float64), Shape__Len (float64)
