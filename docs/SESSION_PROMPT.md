# Kickoff prompt for a Claude session connected to this repo

Paste the text below into a new session that has this repository attached. Fill in the bracketed
parts. Repeat with a shorter version ("New data in data/raw, rerun and report") for later sessions.

---

I've added my property data to `data/raw/`. Read README.md and CLAUDE.md, then:

1. Install requirements and run `scripts/01_inventory.py`. Tell me if any layer is missing a
   coordinate system, has unexpected geometry, or has fields that don't match what you expected.
2. Update `config.yaml` to match my data:
   - Project CRS: [e.g. EPSG:2272, Pennsylvania South, US feet]
   - Parcel layer: [file and layer name]; unique ID field: [field]; recorded acreage field: [field or none]
   - Overlay layers and the attribute to summarise each by: [e.g. wetlands by WETLAND_TYPE, zoning by ZONE]
3. Run `./run_all.sh`. Review `outputs/qa_report.md` and flag any overlaps, gaps, or parcels that
   don't join cleanly before going further.
4. Give me a summary of total acreage, per-parcel acreage versus deed acreage, and acres and
   percent of the property under each overlay class.
5. Look at the static maps and interactive map and tell me whether anything looks wrong.
6. Commit the config, outputs, and any script changes to a branch and push it.

Questions I care most about: [e.g. how much of the site is developable after wetlands and
setbacks; which parcel has road frontage; where the steepest ground is].

Don't change the analysis scripts' logic without telling me why. If a result looks off, say so
rather than adjusting it.
