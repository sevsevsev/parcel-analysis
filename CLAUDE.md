# Project conventions for Claude sessions

A land-shopping evaluator: each listing is `listings/<name>.yaml`, run with `./run_all.sh <name>`.
Read `README.md` first.

## Workflow
- `pip install -r requirements.txt` once per session before any script.
- New listing: parcels into `data/raw/<name>/`, copy `listings/_template.yaml`, run
  `./run_all.sh <name>`, read `outputs/<name>/qa_report.md` before trusting anything else.
- Scripts are numbered and read everything from the listing config (`PROPERTY_CONFIG`). Never
  hard-code paths, field names, thresholds or a CRS in a script; add a config key.
- Public data goes in `sources.yaml` with a trimmed `out_fields` list and a `role`. Listings
  reference sources with `use: <key>`. Do not paste service URLs into listing files.
- Shared helpers: `_common.py` (config, layers, units), `_fetch.py` (remote sources), `_maps.py`
  (figures). Area and length go through `area_acres()` / `length_feet()`.
- Test on the synthetic site (`./run_all.sh sample`) before running a real listing after changing
  a script. `tests/make_sample_data.py` regenerates it.
- Commit `data/cache/<listing>/` and `outputs/<listing>/` so results are reviewable without
  rerunning and don't drift when a service updates. Nothing over 100 MB.

## Analysis rules
- Property totals come from the dissolved boundary, never the sum of parcels.
- Acres to 3 decimals, percentages to 1 decimal.
- A surprising result (coverage over 100%, aspect that contradicts flow direction, a parcel count
  change) means stop and explain, not adjust.
- Evaluation thresholds (`evaluation:` in the listing) are assumptions until checked against the
  municipal ordinance. Say so in any summary.
- Sun modelling is terrain-only; always state that trees are not modelled.
- Basemap: `Esri.WorldImagery`. `OpenStreetMap.Mapnik` blocks automated requests.
- Parcel exports contain owner names and assessment data. Keep them in the repo; never publish
  them to a shared artifact or external service.

## Adding an analysis or a data source
- New step: `scripts/09_<name>.py` following the existing pattern (load config, read
  `outputs/<listing>/property.gpkg` or `evaluation.gpkg`, write markdown + CSV/GeoPackage, add a
  row to the README table). Add its key numbers to `evaluation.json` if the report should show them.
- New public source: an entry in `sources.yaml`. Query the service first to learn its real field
  names and `maxRecordCount`; some services time out with `outFields=*`.
- New county: find its ArcGIS REST services (PASDA for Pennsylvania), add zoning, sewer, water,
  buildings, roads and parcels with roles, then listings there can `use:` them.

## Things that need ArcGIS Pro
Print layouts, licensed toolboxes, Network Analyst. Write an ArcPy script or instructions in
`docs/` for the user to run locally.
