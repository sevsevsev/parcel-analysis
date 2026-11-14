"""PDF map atlas for a listing: one page per map with an explanation of the layer, its source,
and what it shows on this site. Builds outputs/<listing>/atlas.html and renders atlas.pdf with
the pre-installed Chromium (via node + playwright)."""
import base64
import html
import io
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import geopandas as gpd
import pandas as pd
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from _common import area_acres, length_feet, load_config  # noqa: E402

CSS = """
@page { size: Letter; margin: 0.6in 0.6in 0.7in 0.6in; }
body { font: 10.5pt/1.45 Georgia, 'Times New Roman', serif; color: #111; margin: 0; }
h1 { font: 700 22pt/1.2 Helvetica, Arial, sans-serif; margin: 0 0 6pt; }
h2 { font: 700 15pt/1.2 Helvetica, Arial, sans-serif; margin: 0 0 4pt; }
h3 { font: 700 11pt/1.2 Helvetica, Arial, sans-serif; margin: 10pt 0 3pt; }
.page { page-break-after: always; }
.page:last-child { page-break-after: auto; }
.kicker { font: 9pt Helvetica, Arial, sans-serif; color: #666; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 2pt; }
.map { width: 100%; max-height: 5.9in; object-fit: contain; display: block; margin: 6pt 0 8pt; border: 1px solid #ccc; }
.two .map { max-height: 3.6in; }
.src { font: 8.5pt Helvetica, Arial, sans-serif; color: #555; margin-top: 6pt; }
table { border-collapse: collapse; width: 100%; font: 9pt Helvetica, Arial, sans-serif; margin: 4pt 0 6pt; }
th, td { border-bottom: 1px solid #ddd; padding: 2.5pt 5pt; text-align: left; vertical-align: top; }
th { background: #f2f2f2; } td.n, th.n { text-align: right; }
p { margin: 0 0 6pt; }
.cover p { font-size: 11.5pt; }
.toc li { margin: 2pt 0; }
.note { background: #f7f5ee; border-left: 3px solid #b45309; padding: 5pt 8pt; margin: 6pt 0; font-size: 9.5pt; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 10pt; }
"""


def img(path, width=1500):
    if not path.exists():
        return ""
    im = Image.open(path).convert("RGB")
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85, optimize=True)
    return f'<img class="map" src="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}">'


def table(df, max_rows=14):
    if df is None or len(df) == 0:
        return ""
    df = df.head(max_rows)
    num = {c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])}
    head = "".join(f'<th class="{"n" if c in num else ""}">{html.escape(str(c))}</th>' for c in df.columns)
    rows = "".join("<tr>" + "".join(
        f'<td class="{"n" if c in num else ""}">{html.escape("" if pd.isna(r[c]) else (f"{r[c]:,.3f}".rstrip("0").rstrip(".") if isinstance(r[c], float) else str(r[c])))}</td>'
        for c in df.columns) + "</tr>" for _, r in df.iterrows())
    return f"<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>"


def csv(out, name):
    p = out / name
    return pd.read_csv(p) if p.exists() else None


def page(kicker, title, body, image_html, source=""):
    return (f'<section class="page"><div class="kicker">{html.escape(kicker)}</div><h2>{html.escape(title)}</h2>'
            f'{image_html}{body}{f"<div class=src>{source}</div>" if source else ""}</section>')


def main():
    cfg = load_config()
    out, name = cfg["_out"], cfg["name"]
    E = json.loads((out / "evaluation.json").read_text())
    B, S, W, V, thr = E["buildable"], E["sun"], E["stormwater"], E["services"], E["thresholds"]
    idf = cfg["parcels"]["id_field"]
    lab = cfg["parcels"].get("label_field") or idf
    parcels = gpd.read_file(out / "property.gpkg", layer="parcels")
    labels = dict(zip(parcels[idf].astype(str), parcels[lab].astype(str)))
    meas = csv(out, "parcel_measurements.csv")
    sources = {}
    for p in (cfg["_root"] / cfg["cache_dir"]).glob("*.json"):
        sources[p.stem] = json.loads(p.read_text())
    catalog = yaml.safe_load(open(cfg["_root"] / "sources.yaml"))
    pages = []

    # ---- cover
    summary = out / "summary.md"
    summary_html = ""
    if summary.exists():
        txt = summary.read_text()
        sec = txt.split("## Reading it as a buyer")
        if len(sec) > 1:
            paras = [p for p in sec[1].strip().split("\n\n") if p and not p.startswith("Numbers come")]
            summary_html = "<h3>In short</h3>" + "".join(f"<p>{html.escape(p.replace(chr(10), ' '))}</p>" for p in paras)
    toc = ["Parcels", "Slope", "Buildable area", "Winter sun", "Stormwater", "Growing ground"]
    ov_specs = [s for s in cfg.get("overlays") or [] if (out / f"map_overlay_{s['name']}.png").exists()]
    toc += [s.get("description") or s["name"] for s in ov_specs] + ["Data sources"]
    pages.append(
        f'<section class="page cover"><div class="kicker">Map atlas</div><h1>{html.escape(name.replace("_", " ").title())}</h1>'
        f'<p>{len(parcels)} parcels, {B["property_acres"]:.2f} acres (dissolved). Prepared {date.today():%B %d, %Y} from county parcel '
        f'lines and public geospatial services. Each page shows one map, what the layer is and where it comes from, and what it '
        f'shows on this site. Thresholds used: slope limit {thr.get("max_build_slope_pct", 15)}%, property-line setback '
        f'{thr.get("property_line_setback_ft", 50)} ft, stream buffer {thr.get("stream_buffer_ft", 100)} ft, wetland buffer '
        f'{thr.get("wetland_buffer_ft", 50)} ft. These are working assumptions until checked against the municipal ordinance.</p>'
        f'{("<p class=note>" + html.escape(str(cfg["notes"]).strip()) + "</p>") if cfg.get("notes") else ""}'
        f'{summary_html}<h3>Contents</h3><ol class="toc">{"".join(f"<li>{html.escape(t)}</li>" for t in toc)}</ol></section>')

    # ---- parcels
    m = meas.copy() if meas is not None else None
    if m is not None:
        m.insert(1, "address", m[idf].astype(str).map(labels))
        m = m[[c for c in (idf, "address", "acres_computed", "acres_recorded", "difference_pct", "perimeter_ft") if c in m.columns]]
    total_rec = f" The recorded (deed) acreage totals {meas['acres_recorded'].sum():.2f} acres." if meas is not None and "acres_recorded" in meas else ""
    pages.append(page("Base map", "Parcels",
        f"<p>County parcel polygons for the listing (yellow dashed lines) over current aerial imagery, with the dissolved outer "
        f"boundary in red. Areas are computed from the geometry in {html.escape(cfg['crs'])} after reprojection from the county's "
        f"export, so they are the mapped acreage, which can differ from deed acreage.{total_rec} Parcel lines from county GIS are "
        f"compiled from deeds and tax maps and are not a survey; expect differences of a few feet along boundaries.</p>" + table(m),
        img(out / "map_parcels.png"), "Parcels: county assessment export in the repository. Imagery: Esri World Imagery."))

    # ---- slope
    sc = csv(out, "slope_by_class.csv")
    steep = sc[sc["slope_class"].str.contains("15-25|>25")]["acres"].sum() if sc is not None else 0
    pages.append(page("Terrain", "Slope",
        f"<p>Percent slope derived from the USGS 3DEP digital elevation model at {next((r.get('resolution', 5) for r in cfg.get('rasters') or [] if r.get('role') == 'dem'), 5)} ft "
        f"resolution, with 10 ft contours. Green is gentle, red is steep. Slope matters for three reasons: most municipalities "
        f"restrict building on slopes above 15% or 25%, driveways and septic fields need gentle ground, and steep ground erodes when "
        f"disturbed. On this site {steep:.1f} acres ({100 * steep / B['property_acres']:.0f}%) are steeper than 15%.</p>" + table(sc),
        img(out / "map_slope.png"), "Elevation: USGS 3DEP (elevation.nationalmap.gov). Slope computed in scripts/06_terrain.py."))

    # ---- buildable
    rb = B["removed_by"]
    pads = pd.DataFrame(B["pads"])
    if len(pads):
        pads["parcel"] = pads["parcel"].astype(str).map(lambda x: labels.get(x, x))
    pages.append(page("Evaluation", "Buildable area",
        f"<p>Yellow is ground that passes every test: slope at or below {thr.get('max_build_slope_pct', 15)}%, more than "
        f"{thr.get('property_line_setback_ft', 50)} ft from the outer property line, outside mapped flood zones, and more than "
        f"{thr.get('stream_buffer_ft', 100)} ft from streams and {thr.get('wetland_buffer_ft', 50)} ft from wetlands. Shaded areas show "
        f"which constraint removes each part. Black outlines are contiguous buildable patches of at least "
        f"{thr.get('min_building_pad_acres', 0.5)} acres, the candidate building pads.</p>"
        f"<p><b>{B['buildable_acres']:.2f} acres ({B['buildable_pct']}%) are buildable.</b> Removed by: " +
        ", ".join(f"{k.replace('_', ' ')} {v:.2f} ac" for k, v in rb.items() if v > 0.01) +
        f". Accepting slopes up to 25% would give {B['buildable_if_slope_25_acres']:.2f} acres.</p>" + table(pads) +
        "<p class=note>The setback is applied uniformly to the outer boundary, not per zoning yard rules, and the slope limit is a "
        "placeholder. Both are set in the listing file and should be matched to the ordinance.</p>",
        img(out / "map_buildable.png"), "Computed in scripts/07_site_evaluation.py from the DEM and the overlay layers below."))

    # ---- sun
    asp = csv(out, "aspect_classes.csv")
    pages.append(page("Evaluation", "Winter sun",
        f"<p>Left: hours of direct sun on December 21, the shortest day, found by casting shadows across the elevation model every "
        f"half hour from sunrise to sunset at latitude {S['latitude']}. Right: a winter solar index that also accounts for the "
        f"angle at which sunlight strikes the slope, relative to flat open ground (1.0). A south-facing slope scores above 1, a "
        f"north-facing slope below, because low winter sun hits it obliquely.</p>"
        f"<p>Flat open ground here gets {S['dec21_hours_at_flat_unshaded']} hours. The property averages {S['dec21_sun_hours_property_mean']} h "
        f"(index {S['dec21_solar_index_property']}); the buildable area averages {S['dec21_sun_hours_buildable_mean']} h "
        f"(index {S['dec21_solar_index_buildable']}). {S['south_or_flat_pct']}% of the ground faces south-east to south-west or is flat.</p>"
        "<p class=note>The elevation model is bare earth. Tree canopy and neighbouring buildings are not included, so on a wooded "
        "site real sun at ground level is lower than shown until clearing.</p>" + table(asp),
        '<div class="two">' + img(out / "map_sun_dec21.png") + img(out / "map_solar_index_dec21.png") + '</div>',
        "Computed in scripts/07_site_evaluation.py. Solar geometry from standard declination and hour-angle formulas."))

    # ---- stormwater
    outl = pd.DataFrame(W["outlets"])
    if len(outl):
        outl["parcel"] = outl["parcel"].astype(str).map(lambda x: labels.get(x, x))
    soils = W.get("soils") or {}
    soil_txt = ""
    if soils:
        soil_txt = (f" Soils: hydrologic groups {', '.join(f'{k} {v}%' for k, v in soils['hydrologic_group_pct'].items())}; "
                    f"{soils['good_infiltration_pct(A/B)']}% of the site is group A or B, which infiltrates rainfall well. "
                    f"Hydric soils {soils['hydric_acres']:.2f} ac, poorly drained {soils['poorly_drained_acres']:.2f} ac.")
    pages.append(page("Evaluation", "Stormwater",
        f"<p>Blue lines show where water concentrates as it flows downhill, from filling depressions in the elevation model and "
        f"routing each cell to its steepest neighbour. Darker blue carries more upslope area. Orange dots mark where concentrated "
        f"flow leaves the property, labelled with the acres draining to that point. Magenta marks depressions that would pond "
        f"more than half a foot deep. Cyan lines are mapped streams, green is mapped wetland.</p>"
        f"<p>{W['runon_from_offsite_acres']:.2f} acres of neighbouring land drain onto the property. About "
        f"{W['concentrated_flow_path_ft']:.0f} ft of concentrated flow paths (at least {W['flow_path_threshold_acres']} acre "
        f"contributing) cross it, and {W['ponding_acres']:.3f} acres would pond.{soil_txt}</p>" + table(outl) +
        "<p class=note>This shows where water wants to go on the natural ground. It does not model pipes, culverts, road ditches "
        "or existing stormwater facilities.</p>",
        img(out / "map_stormwater.png"), "Flow routing in scripts/07_site_evaluation.py (D8 on USGS 3DEP). Soils: USDA SSURGO."))

    # ---- growing
    Gr = E.get("growing")
    if Gr and (out / "map_growing.png").exists():
        t = Gr.get("thresholds", {})
        gc = csv(out, "growing_by_class.csv")
        pages.append(page("Evaluation", "Growing ground",
            f"<p>Ground classed for cultivation rather than construction, so no property-line setback is applied. Green is "
            f"garden-grade: slope at or below {t.get('garden_max_slope_pct', 8)}%, at least {t.get('garden_min_jun_sun_h', 8)} hours of "
            f"direct sun on June 21, and soil that is not poorly drained, hydric or mapped wetland. Light green suits orchards and "
            f"terraced beds (slope to {t.get('orchard_max_slope_pct', 20)}%); fruit trees tolerate slopes well and benefit from the cold-air "
            f"drainage a hillside gives. Straw is pasture or meadow (slope to {t.get('pasture_max_slope_pct', 25)}%). Blue is wet ground, "
            f"better for a wet meadow or pond than vegetables. Brown is steep or shaded ground best left as woodlot.</p>"
            f"<p><b>{Gr['garden_acres']:.2f} acres are garden-grade, {Gr['orchard_acres']:.2f} acres orchard or terrace, "
            f"{Gr['pasture_acres']:.2f} acres pasture.</b> {Gr['cultivable_outside_buildable_acres']:.2f} acres of garden and orchard ground "
            f"lie outside the buildable area. Counting building, growing and grazing together, "
            f"{Gr['usable_acres_build_or_grow_or_graze']:.2f} acres ({Gr['usable_pct']}%) of the property are usable. USDA rates "
            f"{Gr['prime_farmland_acres']:.2f} acres as prime farmland soil and {Gr['statewide_importance_acres']:.2f} acres as farmland "
            f"of statewide importance.</p>" +
            (f"<p>Mapped tree canopy covers {Gr['canopy']['canopy_pct_property']}% of the property. "
             f"{Gr['canopy']['buildable_under_canopy_acres']:.2f} acres of buildable ground and "
             f"{Gr['canopy']['cultivable_under_canopy_acres']:.2f} acres of garden or orchard ground are under trees today, so the sun "
             f"figures for those areas apply only after clearing.</p>" if Gr.get("canopy") else "") + table(gc) +
            "<p class=note>Sun is modelled on bare earth; a wooded site needs clearing before the sun figures apply. Soil fertility, "
            "stoniness and deer pressure are not in any public layer and need a site visit and a soil test.</p>",
            img(out / "map_growing.png"), "Computed in scripts/07_site_evaluation.py from the DEM, sun model and USDA SSURGO soils."))

    # ---- overlays
    ovl_gpkg = out / "overlays.gpkg"
    for spec in ov_specs:
        n, cls = spec["name"], spec.get("class_field")
        desc = spec.get("description") or n.replace("_", " ")
        src = sources.get(n, {})
        byc = csv(out, f"overlay_{n}_by_class.csv")
        try:
            lyr = gpd.read_file(ovl_gpkg, layer=n)
        except Exception:  # noqa: BLE001
            lyr = None
        what = ""
        if lyr is not None and len(lyr) == 0:
            what = "<p>No features of this layer fall on the property. The map shows the surrounding area for context.</p>"
        elif lyr is not None and lyr.geom_type.isin(["LineString", "MultiLineString"]).any():
            what = f"<p>{len(lyr)} feature(s) cross the property, {length_feet(lyr.geometry).sum():,.0f} ft in total.</p>"
        elif byc is not None and len(byc):
            cov = byc["acres"].sum()
            what = (f"<p>Covers {cov:.2f} acres ({100 * cov / B['property_acres']:.1f}% of the property).</p>" + table(byc))
        # layer-specific guidance
        role = spec.get("role")
        guide = {
            "zoning": "Zoning sets minimum lot size, setbacks, height and permitted uses. The district name usually encodes the minimum lot; the ordinance link in the table gives the yard requirements that should replace the uniform setback used here.",
            "sewer": "Being inside a sewer authority's service area means a connection may be available, not that a lateral exists at the lot. Outside the area, a house needs an on-site septic system, which depends on soils and slope.",
            "water": "Public water service area. Outside it, a well is needed.",
            "soils": "USDA soil survey map units with the dominant component's hydrologic group (A drains fastest, D slowest), drainage class, hydric rating and depth to a restrictive layer. These drive septic feasibility, stormwater infiltration and foundation drainage.",
            "floodplain": "FEMA flood hazard zones. Zone A and AE are the 1% annual-chance (100-year) floodplain, where building is restricted and flood insurance is required with a mortgage. Zone X is outside the mapped floodplain.",
            "wetlands": "National Wetlands Inventory polygons are mapped from aerial imagery, not field delineation. They indicate where a delineation is likely needed; regulated wetlands can exist that are not mapped, and mapped ones can be wrong by tens of feet.",
            "streams": "Mapped stream channels. Pennsylvania municipalities commonly require riparian buffers of 50 to 150 ft, and earth disturbance near streams needs permits.",
            "waterbodies": "Mapped ponds and lakes.",
            "canopy": "Tree canopy outlines mapped from lidar and imagery. The sun model ignores trees, so this layer shows where the modelled sun is not yet real, and what clearing a garden or house site would involve.",
            "zoning_overlays": "Zoning overlay districts and supplemental controls that add rules on top of the base district: floodplain, steep slope, watershed, historic and sign controls. Each carries its code section.",
            "steep_slope_overlay": "A regulatory steep slope area: earth moving and building on slopes above the code threshold need review and may be limited. This is the legal counterpart of the slope map earlier in the atlas.",
            "buildings": "Building footprints from the county assessment. Useful for spotting structures, encroachments across lot lines, and what a neighbour has built.",
            "roads": "Street centerlines with ownership. Frontage on a state road can mean a PennDOT highway occupancy permit for a new driveway; municipal roads are handled by the township.",
        }.get(role, "")
        fetched = src.get("fetched_at", "")[:10]
        srcline = f"{html.escape(src.get('url', spec.get('path', '')))}" + (f", fetched {fetched}" if fetched else "")
        if src.get("copyright"):
            srcline += f". {html.escape(src['copyright'][:160])}"
        pages.append(page("Overlay", desc, f"<p>{html.escape(guide)}</p>{what}", img(out / f"map_overlay_{n}.png"), srcline))

    # ---- sources
    rows = []
    for spec in [dict(cfg["parcels"], name="parcels")] + list(cfg.get("overlays") or []) + list(cfg.get("rasters") or []):
        s = sources.get(spec["name"], {})
        rows.append({"layer": spec["name"], "source": spec.get("source", "file"),
                     "detail": s.get("url") or spec.get("path", ""), "fetched": s.get("fetched_at", "")[:10]})
    pages.append(page("Appendix", "Data sources",
        "<p>Remote layers were fetched for the parcels' extent plus a margin and cached in the repository, so the maps can be "
        "regenerated and will not change until the cache is refreshed. Parcel lines and assessment attributes are the county's "
        "export. The elevation model is bare earth lidar from USGS 3DEP.</p>" + table(pd.DataFrame(rows), 40), ""))

    doc = (f"<!DOCTYPE html><html><head><meta charset=utf-8><title>{html.escape(name)} map atlas</title><style>{CSS}</style></head>"
           f"<body>{''.join(pages)}</body></html>")
    html_path = out / "atlas.html"
    html_path.write_text(doc)
    pdf_path = out / "atlas.pdf"
    js = f"""
    const {{ chromium }} = require('playwright');
    (async () => {{
      const b = await chromium.launch(); const p = await b.newPage();
      await p.goto('file://{html_path}', {{ waitUntil: 'load' }});
      await p.pdf({{ path: '{pdf_path}', format: 'Letter', printBackground: true,
                    displayHeaderFooter: true, headerTemplate: '<span></span>',
                    footerTemplate: '<div style="font:8px Helvetica,Arial;color:#777;width:100%;text-align:center">{html.escape(name)} map atlas &nbsp; page <span class="pageNumber"></span> of <span class="totalPages"></span></div>' }});
      await b.close();
    }})();"""
    subprocess.run(["node", "-e", js], check=True)
    print(f"wrote {pdf_path.relative_to(cfg['_root'])} ({pdf_path.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
