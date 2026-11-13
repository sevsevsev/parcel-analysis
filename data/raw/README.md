# data/raw

Put exported layers here. Nothing in this folder is read unless it is referenced in `config.yaml`.

Preferred: one GeoPackage (e.g. `property.gpkg`) containing layers such as `parcels`, `wetlands`,
`zoning`, `floodplain`, `easements`, `soils`, `roads`, `streams`. Shapefiles and GeoJSON also work.
Rasters (DEM, imagery) as GeoTIFF, clipped to the site.

Every layer must have a defined coordinate system. Check with `python3 scripts/01_inventory.py`.
