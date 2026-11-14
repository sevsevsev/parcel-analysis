# Web app plan: address in, evaluation out

Goal: a small web app where a user types an address (or clicks parcels on a map), picks what to
analyse, and gets the same report, maps and PDF the repository produces today, in a minute or
two, at near-zero running cost. This document is the MVP design, with the measurements that
drove it.

## 1. Where the time goes today

Measured on the Port Royal listing (one parcel, 17 remote layers), November 14, 2026:

| Step | Cold | Warm (cached data) | Depends on |
|---|---|---|---|
| Fetch 17 vector layers, sequential | 34 s | 0 | location |
| of which: DEM export (USGS 3DEP) | 23 s | 0 | location |
| of which: Philadelphia zoning overlays (9 MB, citywide polygons) | 10 s | 0 | location |
| Parcel QA, measurements, overlays, terrain | 6 s | 6 s | parcels |
| Site evaluation (sun shadow casting ~20 s, flow routing, growing) | 28 s | 28 s | location + parcels |
| Static maps (17 PNGs; basemap tiles are the cost, 5.6 s for the first) | 36 s | 36 s | parcels |
| HTML report | 3 s | 3 s | parcels |
| PDF atlas (Chromium) | 5 s | 5 s | parcels |
| **Total** | **~2 min** | **~80 s** | |

Everything that is expensive depends on the *location* (a DEM tile, a basemap tile, a zoning
polygon), not on which parcels the user picked. Two listings a street apart should share almost
all of it. That is the whole optimisation strategy.

## 2. User flow

1. **Address box.** Census Geocoder (free, no key) returns coordinates and the county FIPS.
   Fallback: click the map.
2. **Parcel picker.** The county registry maps FIPS to a parcel service. A point query returns
   the parcel under the address, drawn on the map. The user clicks neighbours to add them to the
   listing (each click is one point query, under a second) and can remove any. The list of
   parcel IDs plus the county becomes the listing.
3. **Layer picker.** Checklist grouped by purpose with a preset selector:
   - *Quick look* (about 20 s): parcels, zoning, flood zones, wetlands, slope, buildable area.
   - *Build* adds setbacks, streams, soils, sewer and water, buildings, roads, winter sun, stormwater.
   - *Grow* adds growing ground, canopy (where available), frost-free days, prime farmland.
   - *Full due diligence* adds historic, easements, preserved farmland, transmission, traffic,
     DEP streams, taxes, septic ratings.
   Each layer shows its last measured fetch time and whether it is already cached for this area,
   so the user sees what a tick costs. Thresholds (slope limit, setback, buffers) are editable
   with the defaults from the listing template.
4. **Run.** A job starts; the page shows per-step progress and streams the quick-look results
   (parcels, acreage, zoning, flood, slope) as soon as they exist, then the full evaluation.
5. **Results.** The existing `report.html` served in-page, `atlas.pdf` generated on demand by a
   button rather than on every run, GeoPackages for download. A share link with a random token.
   A "compare" page lists the user's listings side by side (today's `compare.py`).

## 3. Architecture (MVP)

One container, no managed services, so it runs on a $5 to $10 a month host.

- **Backend:** FastAPI. Endpoints: `POST /geocode`, `GET /parcel?lat&lon`, `POST /listings`
  (parcel IDs, county, layers, thresholds) returns a job id, `GET /jobs/{id}` for progress,
  `GET /listings/{id}/report`, `/atlas.pdf`, `/data.gpkg`.
- **Worker:** the existing scripts, called as functions rather than subprocesses, run by a
  single background worker process (a queue table in SQLite; Redis is not needed at MVP scale).
  Concurrency 1 to 2 jobs; the sun model is CPU-bound.
- **Storage:** filesystem. `cache/` for location-keyed data, `listings/<id>/` for per-listing
  outputs, SQLite for jobs, listings and cache index. A persistent volume on the host.
- **Frontend:** one static page with MapLibre or Leaflet, Esri imagery tiles, the address box,
  parcel picker, layer checklist and a results view. No framework needed at MVP.
- **Registry:** `counties.yaml`: FIPS to {parcel service URL, ID field, label field, deed-acres
  field, CRS, catalog block}. Start with Montgomery and Philadelphia (done), then Bucks, Chester,
  Delaware and Berks (parcel services verified on PASDA; zoning for Bucks and Delaware).
- **Hosting:** Fly.io, Railway or Render with a Docker image carrying the GDAL stack and
  Chromium (for PDFs). Vercel is not suitable: the geospatial libraries and two-minute jobs need
  a persistent container, not serverless functions.

## 4. Keeping fetch cost down

Every source is free; the costs are wall-clock time, politeness to public servers, and egress
on the host. Levers, in order of payoff:

1. **Location-keyed cache with per-source TTL.** Key every fetch by source plus a 1 km grid
   cell of the AOI, not by listing. DEM tiles, slope, aspect, flow routing and the sun rasters
   are derived once per cell and kept forever (terrain does not change). Soils, wetlands, flood
   zones: 180 days. Parcels, zoning, buildings: 30 days. Second listing in the same area then
   skips the 23 s DEM export and the 20 s sun model entirely.
2. **Cache basemap tiles on disk** (`contextily.set_cache_dir`) and render one imagery
   backdrop per AOI, reused by all 17 maps. Expected: maps from 36 s to under 10 s.
3. **Fetch in parallel.** Six concurrent requests with `httpx` instead of sequential; the 34 s
   cold fetch becomes about 12 s, bounded by the slowest service.
4. **Fetch only what was ticked**, and only the fields in the catalog (already trimmed).
5. **Tighter AOI for heavy layers.** Request citywide-polygon layers (Philadelphia zoning
   overlays, 9 MB) with the AOI as the query geometry *and* ask the server to clip
   (`geometryPrecision`, `outSR`, `returnGeometry` with `quantizationParameters`), or fall back
   to the generalised overlay layer. Expected: 10 s to under 2 s.
6. **PDF on demand**, not per run (5 s and Chromium memory saved on most runs).
7. **Quick-look first.** The 20 s preset answers "is this worth a look" before the two-minute run.
8. **Rate limits and retries** per host (already have retries with backoff); a global cap of a
   few requests per second per host so a burst of users does not get the app blocked.

With 1 to 4 done, a cold run drops to roughly 50 to 60 s and a warm run (same area, different
parcels) to about 40 s, most of it the sun model and maps. A "fast sun" option (two dates,
20-minute steps) would halve that if needed.

## 5. What is reused from this repo unchanged

The whole pipeline: `sources.yaml` catalog, `definitions.yaml`, `_fetch.py`, QA, measurements,
overlays, terrain, site evaluation, growing ground, restrictions, report and atlas generators.
The app writes a listing YAML and calls the same code, so the command-line path and the web
path cannot drift apart, and every web result is reproducible from the repo.

## 6. Build phases

| Phase | Work | Effort |
|---|---|---|
| 1. Library and cache | Turn `run_all.sh` into a Python function with step callbacks; location-keyed cache with TTLs; parallel fetch; basemap tile cache; `counties.yaml` with the six PA counties | 2 days |
| 2. API and worker | FastAPI endpoints, SQLite job queue, worker loop, progress events, share tokens, Dockerfile with GDAL + Chromium | 1.5 days |
| 3. Front end | Address box, geocode, parcel picker with click-to-add, layer presets and checklist, threshold form, progress view, results view, compare page | 2 days |
| 4. Deploy and harden | Host with persistent volume, rate limits, error reporting, a nightly cache sweep, a smoke test that runs the sample listing | 1 day |

About a week and a half of work for an MVP covering the Montgomery, Philadelphia, Bucks, Chester,
Delaware and Berks parcel services, with any US address getting the national layers (flood,
wetlands, hydrography, soils, elevation, roads, historic, traffic where PennDOT applies).

## 7. Risks and open questions

- **Parcel services vary.** Some counties sell parcels or offer only downloads; the registry
  must say "not available, upload a shapefile" gracefully. The upload path is the current
  `data/raw` flow and stays in the app.
- **Zoning is municipal.** Where no county or municipal service exists, the app reports
  "zoning not available" and links to the municipality.
- **Public servers go down** (FEMA, USGS and the hydrography service all failed at least once
  during development). Retries plus the cache cover most of it; the report marks skipped layers.
- **Imagery terms.** Esri World Imagery tiles are free with attribution for light use; a public
  app should register a free ArcGIS developer key and respect its tile quota, or switch the
  static maps to USGS NAIP imagery, which is public domain.
- **Owner names** are in parcel exports and the county parcel services. The app should strip
  owner fields before anything is displayed or shared.
- **Not a survey, not legal advice.** The report's caveats must stay visible on every page.
