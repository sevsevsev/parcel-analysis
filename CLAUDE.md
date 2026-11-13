# Project conventions for Claude sessions

This repo analyses a property made of several parcels. Read `README.md` first.

## Workflow
- Run `pip install -r requirements.txt` once per session before any script.
- Always start with `python3 scripts/01_inventory.py` after new data arrives, then `./run_all.sh`.
- Scripts are numbered and read everything from `config.yaml` (or `PROPERTY_CONFIG=...`). Do not
  hard-code paths, field names or a CRS in scripts; add a config key instead.
- Shared helpers live in `scripts/_common.py`. Area and length must go through `area_acres()` and
  `length_feet()` so unit handling stays in one place.
- Test changes on the synthetic data (`PROPERTY_CONFIG=config.sample.yaml ./run_all.sh`) before
  running on real data. `tests/make_sample_data.py` regenerates it.
- Commit generated outputs (`outputs/*.md`, `*.csv`, `*.png`, `*.html`, `*.gpkg`) so results are
  reviewable without rerunning. Do not commit anything over 100 MB.

## Analysis rules
- Totals for the property come from the dissolved boundary, never the sum of parcels, because
  parcels can overlap.
- Report acres to 3 decimals and percentages to 1 decimal.
- When a result looks surprising (coverage over 100%, negative remainder, parcel count changed),
  stop and explain it rather than adjusting numbers.
- Basemap: `Esri.WorldImagery` by default. `OpenStreetMap.Mapnik` blocks automated requests.

## Adding a new analysis
Create `scripts/06_<name>.py` following the pattern of the existing steps: load config, read from
`outputs/property.gpkg`, write a markdown summary plus CSV/GeoPackage to `outputs/`, and add the
step to the README table. Maps go through `05_maps.py` or a new numbered map script.

## Things that need ArcGIS Pro
Print-quality layouts, anything requiring licensed toolboxes, and Network Analyst. For those,
write an ArcPy script or step-by-step instructions in `docs/` for the user to run locally.
