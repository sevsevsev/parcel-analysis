# Web app API contract (MVP)

Base URL: same origin as the static front end. All responses JSON unless noted.

## GET /api/geocode?q=<address>
Returns `{ "lat": 40.07, "lon": -75.26, "matched": "331 BARREN HILL RD, ...", "county_fips": "42091", "county_name": "Montgomery County", "state": "PA", "supported": true }`.
`supported` is false when no parcel service is registered for the county (the UI should say so and
offer map-click only for national layers). 404 when no match.

## GET /api/parcel?lat=&lon=
Parcel under a point, from the county's parcel service. Returns
`{ "county_fips": "42091", "parcel_id": "650000463003", "label": "325 BARREN HILL RD", "acres": 5.16, "geometry": <GeoJSON polygon, WGS84> }`
or 404 if nothing there / county unsupported.

## GET /api/counties
`[{ "fips": "42091", "name": "Montgomery County, PA", "layers": [ ... ] }]` where `layers` lists the
catalog keys available there (national ones plus the county block), each as
`{ "key": "nwi_wetlands", "description": "USFWS National Wetlands Inventory", "group": "water", "preset": ["quick","build","grow","full"], "typical_seconds": 2 }`.

## GET /api/presets
`{ "quick": ["fema_flood","nwi_wetlands","<zoning key>", ...], "build": [...], "grow": [...], "full": [...] }` as catalog keys, resolved per county by the front end using /api/counties.

## POST /api/listings
Body:
```json
{ "county_fips": "42091", "parcel_ids": ["650000463003", "650000454003"], "title": "optional",
  "layers": ["fema_flood", "nwi_wetlands", "montco_zoning"],
  "thresholds": { "max_build_slope_pct": 15, "property_line_setback_ft": 50, "stream_buffer_ft": 100,
                  "wetland_buffer_ft": 50, "drainage_way_threshold_acres": 5, "drainage_way_buffer_ft": 50,
                  "min_building_pad_acres": 0.5 },
  "growing": { "garden_max_slope_pct": 8, "orchard_max_slope_pct": 20, "pasture_max_slope_pct": 25 },
  "pdf": false }
```
Returns `{ "listing_id": "a1b2c3d4", "job_id": "j_...", "url": "/listing/a1b2c3d4" }`. Everything
except county_fips and parcel_ids is optional; defaults come from the listing template.

## GET /api/jobs/{job_id}
`{ "status": "queued|running|done|failed", "step": "07_site_evaluation", "steps_done": 6, "steps_total": 9,
   "log": ["...last 30 lines..."], "error": null, "listing_id": "a1b2c3d4" }`.

## GET /api/listings/{listing_id}
`{ "listing_id", "title", "county_fips", "parcel_ids", "layers", "created_at", "status",
   "summary": { ...evaluation.json key numbers: property_acres, buildable_acres, buildable_pct,
                garden_acres, usable_pct, dec21_solar_index_buildable, runon_acres, zoning, historic_pct... } or null,
   "files": { "report": "/api/listings/<id>/report", "atlas": "/api/listings/<id>/atlas.pdf" | null,
              "evaluation_json": "...", "property_gpkg": "...", "evaluation_gpkg": "..." } }`.

## GET /api/listings
List of the above (summary form) newest first, for the compare page.

## GET /api/listings/{id}/report  -> text/html (the report page; may be embedded in an iframe)
## GET /api/listings/{id}/atlas.pdf -> application/pdf (generated on first request if missing; may take ~10 s)
## GET /api/listings/{id}/files/<name> -> any output file (gpkg, csv, png, md)
## POST /api/listings/{id}/rerun  body { "layers": [...], "thresholds": {...}, "pdf": bool } -> new job on the same listing

## Static
`/` serves app/static/index.html. `/listing/<id>` serves the same page; the page reads the id
from the path and opens the results view.
