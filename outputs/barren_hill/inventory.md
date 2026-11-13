# Data inventory

### dem_3dep.tif

- CRS: `EPSG:2272`
- Size: 482 x 432 px, 1 band(s), float32
- Resolution: 5.00 x 5.00
- Bounds: 2662737.5, 279184.4 to 2665146.3, 281343.3
- NoData: None

### fema_flood.gpkg :: fema_flood

- CRS: `EPSG:4326`
- Geometry: Polygon
- Features: 1
- Bounds: -75.5, 40.0 to -75.1, 40.3
- Fields: FLD_ZONE (str), ZONE_SUBTY (str), SFHA_TF (str), STATIC_BFE (int64)

### montco_buildings.gpkg :: montco_buildings

- CRS: `EPSG:4326`
- Geometry: Polygon
- Features: 66
- Bounds: -75.3, 40.1 to -75.3, 40.1
- Fields: PARID (str), DESCRIPTIO (str), Category (str), YRBLT (int64), SFLA (int64), STORIES (float64)

### montco_roads.gpkg :: montco_roads

- CRS: `EPSG:4326`
- Geometry: LineString
- Features: 10
- Bounds: -75.3, 40.1 to -75.3, 40.1
- Fields: St_Name (str), St_PosTyp (str), RoadClass (str), SpeedLimit (int64), Owner (str), Status (str), OneWay (str)

### montco_sewer.gpkg :: montco_sewer

- CRS: `EPSG:4326`
- Geometry: Polygon
- Features: 2
- Bounds: -75.3, 40.0 to -75.1, 40.1
- Fields: Name (str), Owner (str), Discharge (str)

### montco_water.gpkg :: montco_water

- CRS: `EPSG:4326`
- Geometry: Polygon
- Features: 1
- Bounds: -75.5, 40.0 to -75.0, 40.2
- Fields: Name (str)

### montco_zoning.gpkg :: montco_zoning

- CRS: `EPSG:4326`
- Geometry: Polygon
- Features: 3
- Bounds: -75.3, 40.1 to -75.2, 40.1
- Fields: Name (str), Code (str), Type (str), Category (str), Municipali (str), WebSite (str), Map_Date (str)

### nhd_flowlines.gpkg :: nhd_flowlines

- CRS: `EPSG:4326`
- Geometry: LineString
- Features: 5
- Bounds: -75.3, 40.1 to -75.3, 40.1
- Fields: gnis_name (object), fcode (int64), ftype (int64)

### nhd_waterbodies.gpkg :: nhd_waterbodies

- CRS: `EPSG:4326`
- Geometry: Polygon
- Features: 3
- Bounds: -75.3, 40.1 to -75.3, 40.1
- Fields: GNIS_NAME (object), FCODE (int64), FTYPE (int64)

### nwi_wetlands.gpkg :: nwi_wetlands

- CRS: `EPSG:4326`
- Geometry: Polygon
- Features: 4
- Bounds: -75.3, 40.1 to -75.3, 40.1
- Fields: ATTRIBUTE (str), WETLAND_TYPE (str)

### ssurgo_soils.gpkg :: ssurgo_soils

- CRS: `EPSG:4326`
- Geometry: MultiPolygon
- Features: 15
- Bounds: -75.3, 40.1 to -75.3, 40.1
- Fields: mukey (str), musym (str), muname (str), farmlndcl (str), compname (str), comppct_r (int64), hydgrp (str), drainagecl (str), hydricrating (str), slope_r (int64), runoff (str), flood_freq (str), resdept_cm (int64), wet_depth_cm (float64)

### BarrenHillParcels.shp

- CRS: `EPSG:3857`
- Geometry: Polygon
- Features: 7
- Bounds: -8378693.7, 4876730.3 to -8378140.2, 4877193.7
- Fields: OBJECTID_1 (int64), OBJECTID_2 (int64), TAXPIN (str), ALTERNATEI (str), PARCELTYPE (str), Shape_Leng (float64), LOCATION_C (object), CLASS (str), NBHD (str), LIV_UNITS (str), UTIL1 (str), UTIL2 (str), UTIL3 (object), TRAFFIC (str), ROADS1 (str), ROADS2 (object), BLOCK (str), UNIT (str), ALT_ID (str), PROP_INFO_ (str), TOTAL_APPR (int64), TOTAL_ASSE (int64), RESTRICTIO (object), FARMLAND (object), OBYVAL (int64), LAND_USE (str), ASMT_CHGDA (str), OWN1 (str), OWN2 (str), CAREOF (str), ADDR1 (str), ADDR2 (object), ADDR3 (str), ZIP1_ZIP2 (str), OWN_INFO_C (str), MUNI_CODE (str), SCH_DIST (str), SUBDIVISIO (object), LOT_NO (str), FRONTFT (int32), LEGAL1 (str), LEGAL2 (object), LEGAL3 (object), LOC_NO (int64), LOC_ADD (object), LOC_DIR (object), LOC_STR (str), LOC_SUF (str), LOC_SUF2 (object), LOC_UNITDE (object), LOC_UNITNO (object), LOCATION1 (str), LOCATION2 (object), LOC_ZIP1_Z (str), LEGAL_CHGD (str), EST_CO_TAX (int64), EST_MUNI_T (int64), EST_SCH_TA (int64), DEED_BOOK (str), DEED_PAGE (str), SALE_DATE (str), CONSIDERAT (int64), STATE_TAX_ (str), STEB (str), LAND_SF (int64), LAND_ACRES (float64), LAND_CHGDA (str), POOL (object), OBY_CHGDAT (object), CONDITION (str), DEGREE_REM (str), YR_REM (object), SFLA (int64), FINBSMT_SF (int32), STORIES (object), EXTWALL (str), BASEMENT (str), FUEL (str), HEAT (str), YEAR_BUILT (int32), STYLE (str), BEDROOMS (object), BATHS (object), HALF_BATHS (object), RM_TOT (object), PREFAB_FRP (object), FRPL_OPEN (object), FRPL_STACK (object), BSMT_CAR (object), DWEL_CHGDA (str), COMM_AREA (int64), COMM_NLA (int64), STRUCTURE (object), USE_TYPE (object), COMM_BSMT (object), COMM_HEAT (object), COMM_AIR (object), COMM_YR_BL (int32), COMM_UNITS (int32), COMM_IDENT (object), PARK_COV (object), PARK_UNCOV (object), PARTITION (object), RESIDUAL (str), ELEV (object), COMM_CHGDA (object), ASSESSMENT (int64), PROP_INFO1 (datetime64[ms]), ASSMT_CHGD (datetime64[ms]), OWN_INFO_1 (datetime64[ms]), LEGAL_CH_1 (datetime64[ms]), SALE_DATE_ (datetime64[ms]), LAND_CHDAT (datetime64[ms]), OBY_CHGD_1 (object), DWEL_CHG_1 (datetime64[ms]), COMM_CHG_1 (datetime64[ms]), PARCEL (str), LANDSF (object), EST_MCCC_T (int64), Muni_Name (str), Shape__Are (float64), Shape__Len (float64), Shape_Le_1 (float64), Shape_Area (float64)
