# Kickoff prompts for a Claude session connected to this repo

## Evaluate a new listing

I've put the parcels for a new listing in `data/raw/<name>/`. Read README.md and CLAUDE.md, then:

1. Create `listings/<name>.yaml` from the template. CRS: [EPSG code or "pick the State Plane zone
   for the site"]. Parcel ID field: [field]. Recorded acreage field: [field or none]. Use the same
   public sources as barren_hill, plus [any extra layer]. Thresholds: [setback ft, max slope %, or
   "keep the defaults and tell me what they are"].
2. Run `./run_all.sh <name>` and read `outputs/<name>/qa_report.md`. Flag any overlaps, gaps or
   parcels that don't join before going on.
3. Open `outputs/<name>/evaluation.md` and the maps. Give me the buyer's summary: buildable acres
   and the biggest building pad, winter sun on that pad, where water comes from and goes, soils,
   zoning, sewer and water, road frontage, existing structures. Say what looks like a problem.
4. Run `python3 scripts/compare.py` and tell me how this listing ranks against the others.
5. Commit the listing config, cache and outputs on a branch and push it.

Don't change analysis logic without telling me why. If a result looks off, say so instead of
adjusting it.

## Add a data source

Add [layer, e.g. "Chester County zoning"] to `sources.yaml`. Find the service, confirm it answers a
small bounding-box query, note its real field names and maxRecordCount, trim `out_fields` to what
the evaluation needs, give it a `role`, and test it on the `sample` listing before committing.

## Change what the evaluation measures

I want the evaluation to also report [e.g. distance from the largest pad to the nearest road, or
acres within 300 ft of a stream]. Add it to `scripts/07_site_evaluation.py` (or a new numbered
step), include the number in `evaluation.json` and the report, test on `sample`, then rerun
`barren_hill` and show me the new numbers.
