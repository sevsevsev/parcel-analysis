# Parcel analysis: a land-shopping evaluator

Give it the parcels of a listing and it pulls the public data that matters, runs a site
evaluation, and writes a report: **how much of the land is buildable, how much sun it gets,
how water moves across it, and what zoning and services apply.** Every listing is a small
config file; every number is reproducible from the repo.

## Quick start

```bash
pip install -r requirements.txt
./run_all.sh barren_hill        # runs every step for listings/barren_hill.yaml
./run_all.sh sample             # synthetic demo site
python3 scripts/compare.py      # side-by-side table of all evaluated listings
```

Open `outputs/<listing>/report.html` for the full report, or `outputs/<listing>/evaluation.md`
for the same content as text. `--refresh` after the listing name re-downloads remote layers.

## Adding a listing

1. Export the listing's parcels from ArcGIS Pro (shapefile or GeoPackage, any CRS) into
   `data/raw/<listing>/`. Or skip the export and pull them from a county parcel service with a
   `where` filter (see `sources.yaml`, `montco_parcels`).
2. Copy `listings/_template.yaml` to `listings/<listing>.yaml`. Set `crs`, the parcel file, the
   ID field, and pick the public sources to use by name. Adjust the `evaluation:` thresholds to the
   municipality (setbacks, steep-slope limit).
3. `./run_all.sh <listing>`.

## Where data comes from

Two kinds of layers, mixed freely in a listing:

- **Files committed to the repo** (`source: file`): the parcels, a survey, easements, anything
  not available publicly.
- **Public services** (`source: arcgis | arcgis_image | wfs | ssurgo | url`): fetched for the
  parcels' extent plus a margin, trimmed to the fields we need, and cached under
  `data/cache/<listing>/` so results don't change under you. `outputs/<listing>/sources.md`
  records what was fetched, from where, and when.

`sources.yaml` is the curated catalog. Today it holds USFWS wetlands, FEMA flood zones, USGS
hydrography, USGS 3DEP elevation, USDA SSURGO soils (polygons plus Soil Data Access attributes),
Census roads, and Montgomery County PA zoning, sewer and water service areas, building outlines,
street centerlines and parcels from PASDA. Add a county's services there once and every listing
can use them. Each entry carries a `role` (wetlands, floodplain, streams, soils, zoning, sewer,
water, buildings, roads, dem) so the evaluator finds layers whatever they are called.

## What the pipeline produces (`outputs/<listing>/`)

| Step | Output | What it does |
|---|---|---|
| `00_fetch.py` | `sources.md`, `data/cache/<listing>/*` | Fetches and caches every remote source for the area of interest |
| `01_inventory.py` | `inventory.md` | Lists every layer: CRS, geometry, feature count, fields |
| `02_qa_parcels.py` | `property.gpkg`, `qa_report.md` | Repairs geometry, finds overlaps, gaps, duplicate IDs; dissolves parcels into one boundary |
| `03_measure.py` | `measurements.md`, `parcel_measurements.csv` | Acres and perimeter per parcel and total, against recorded acreage |
| `04_overlay.py` | `overlays.md`, `overlays.gpkg`, `overlay_*.csv` | Acres and percent of the property under each class of each layer |
| `05_maps.py` | `map_parcels.png`, `map_overlay_*.png`, `map_interactive.html` | Static maps with imagery, scale bar, north arrow; interactive web map |
| `06_terrain.py` | `terrain.md`, `slope_pct.tif`, `aspect_deg.tif`, `hillshade.tif` | Slope and aspect from the DEM; slope classes by parcel |
| `07_site_evaluation.py` | `evaluation.md`, `evaluation.json`, `evaluation.gpkg`, `map_buildable.png`, `map_slope.png`, `map_sun_dec21.png`, `map_solar_index_dec21.png`, `map_stormwater.png`, `map_growing.png` | The evaluation itself (below) |
| `08_report.py` | `report.html` | Self-contained HTML report with scorecard, findings, maps and tables |
| `09_pdf_atlas.py` | `atlas.html`, `atlas.pdf` | PDF map atlas: one page per map with what the layer is, its source, and what it shows here |
| `compare.py` | `outputs/compare.md`, `compare.csv` | One row per listing for shopping across them |

### The site evaluation

- **Buildable area.** Ground at or below the slope limit, outside the property-line setback,
  mapped flood zones, stream and wetland buffers. Reported for the property and each parcel, plus
  the largest contiguous building pads with approximate dimensions and mean slope. A second figure
  shows what accepting slopes to 25% would add.
- **Sun exposure.** Aspect classes, and direct-sun hours on Dec 21, Mar 21 and Jun 21 computed by
  casting shadows across the bare-earth DEM every half hour. A winter solar index compares
  direct-beam energy on each cell to flat open ground, so a north slope scores below 1 and a south
  slope above. Tree canopy is not modelled.
- **Stormwater.** Depression filling and D8 flow routing on the DEM give the off-site area that
  drains onto the property, concentrated flow paths, discharge points along the boundary, and
  depressions that pond. SSURGO soils add hydrologic group (infiltration), drainage class, hydric
  rating and depth to a restrictive layer.
- **Growing ground.** Where food could be grown, with no setback: garden-grade ground (gentle,
  eight or more hours of June sun, dry soil), orchard or terrace ground, pasture, wet ground and
  woodlot, plus USDA prime farmland and statewide-importance acreage. Reported alongside the
  buildable area so gentle sunny land that fails a building test is not written off.
- **Zoning, services, access.** Zoning districts with the ordinance link, percent of the property
  inside public sewer and water service areas, road frontage by road, existing structures.

All GeoPackages open directly in ArcGIS Pro for checking or for print layouts.

## Layout

```
listings/             one YAML per listing (+ _template.yaml, sample.yaml)
sources.yaml          catalog of public services, with trimmed field lists and roles
data/raw/<listing>/   files you export; data/cache/<listing>/ fetched layers (committed)
scripts/              numbered steps; _common.py, _fetch.py, _maps.py are shared helpers
outputs/<listing>/    everything generated
tests/                synthetic sample site generator
docs/                 session prompt and notes
```

## Caveats

Public parcel lines are not a survey. Setbacks and slope limits are configurable guesses until
checked against the municipal ordinance (the zoning table links to it). Sun modelling ignores
trees and neighbouring buildings. Flow routing on a 5 ft DEM shows where water wants to go, not
engineered drainage. Treat the report as a screening tool for deciding which listings deserve a
site visit and a professional review.
