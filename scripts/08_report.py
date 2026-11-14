"""Self-contained HTML report for a listing: scorecard, the buyer's reading, key findings, then
sections with maps and tables, with codes explained where they appear and detail in an appendix.
Everything (images included) is embedded so the file can be emailed or opened anywhere."""
import base64
import html
import io
import json
import re
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from _common import area_acres, cache_path, load_config, property_path  # noqa: E402
from _defs import block_rows, explain_html  # noqa: E402

CSS = """
:root{--bg:#fff;--fg:#1a1a1a;--muted:#666;--line:#e3e3e3;--good:#1a7f37;--warn:#b45309;--bad:#b91c1c;--card:#fafaf7;--note:#1f4e79}
@media(prefers-color-scheme:dark){:root{--bg:#141414;--fg:#eee;--muted:#aaa;--line:#333;--card:#1e1e1c;--note:#8ab4f8}}
body{font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--fg);margin:0;padding:24px 16px;max-width:1100px;margin-inline:auto}
h1{font-size:26px;margin:0 0 4px}h2{font-size:20px;margin:36px 0 10px;border-bottom:1px solid var(--line);padding-bottom:4px}h3{font-size:16px;margin:20px 0 6px}
.sub{color:var(--muted);margin-bottom:20px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:16px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.card .v{font-size:26px;font-weight:650;line-height:1.1}.card .l{color:var(--muted);font-size:13px;margin-top:4px}
.card.good .v{color:var(--good)}.card.warn .v{color:var(--warn)}.card.bad .v{color:var(--bad)}
table{border-collapse:collapse;width:100%;font-size:13.5px;margin:8px 0 16px}th,td{border-bottom:1px solid var(--line);padding:5px 8px;text-align:left;vertical-align:top}th{background:var(--card)}td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:8px;margin:6px 0 14px}
ul.flags{padding-left:0;list-style:none}ul.flags li{margin:6px 0;padding-left:5.2em;text-indent:-5.2em}
.tag{display:inline-block;width:4.6em;text-indent:0;font-size:12px;font-weight:700;text-align:center;border-radius:4px;padding:1px 0;margin-right:.6em;color:#fff}
.tag.bad{background:var(--bad)}.tag.warn{background:var(--warn)}.tag.good{background:var(--good)}.tag.note{background:var(--note)}
.small{font-size:13px;color:var(--muted)}.defs{font-size:13px;background:var(--card);border-left:3px solid var(--line);padding:6px 10px;margin:4px 0 14px}
.defs ul{margin:4px 0 0;padding-left:18px}.buyer p{font-size:15.5px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:700px){.two{grid-template-columns:1fr}}
.gloss dt{font-weight:600;margin-top:6px}.gloss dd{margin:0 0 4px 0;color:var(--muted);font-size:13.5px}
"""

GLOSSARY = [
    ("Dissolved boundary", "The outer line of all the parcels merged into one shape. Property totals use it so overlapping parcel lines are not double counted."),
    ("Buildable area", "Ground that passes every test in the listing file: slope at or below the limit, outside the property-line setback, mapped flood zones, and stream and wetland buffers. The setback and slope limit are assumptions until checked against the municipal ordinance."),
    ("Building pad", "A contiguous patch of buildable ground above the minimum size, with its approximate length and width. Existing houses are not excluded, so a pad can include the current house site."),
    ("Elevation model (DEM)", "A grid of ground heights from USGS lidar (3DEP), 5 ft cells. It is bare earth: trees and buildings are removed, so slope and sun figures describe the ground, not the canopy."),
    ("Winter solar index", "Direct sunlight energy a patch of ground receives on December 21 compared with flat, unshaded ground (1.0). A slope facing the low winter sun scores above 1; a north slope scores below. It accounts for terrain shadows but not trees."),
    ("Run-on", "Rain falling on neighbouring land uphill that flows onto this property before it leaves. Measured as the acres of off-site land that drain across the boundary."),
    ("Flow routing", "Each elevation cell is assumed to drain to its lowest neighbour (the D8 method). Following those links shows where water concentrates and where it leaves the property."),
    ("Hydrologic soil group", "USDA class A to D for how fast a soil absorbs rain when wet. A and B absorb well (good for infiltrating stormwater and septic fields); C and D shed runoff."),
    ("Hydric soil", "Soil that is saturated long enough to be wetland soil. A sign that wetlands may be present even where none are mapped."),
    ("Soil map unit", "The USDA soil survey's named soil type for an area (for example Parker gravelly loam, 15 to 25 percent slopes). The short symbol is the survey's code for it."),
    ("Flood zone X / A / AE", "FEMA's flood hazard classes. X is outside the 1%-a-year (100-year) floodplain. A and AE are inside it; building there needs floodplain permits and flood insurance with a mortgage."),
    ("Wetland code", "National Wetlands Inventory classes mapped from aerial imagery, not a field delineation. PFO is forested wetland, PEM emergent marsh, PSS shrub wetland."),
    ("Aspect", "The compass direction a slope faces, downhill. South and south-west slopes get the most winter sun."),
    ("Drainage way buffer", "A strip kept clear of building along channels the flow model finds, where at least the configured number of acres drain through a cell, even if no stream is mapped there."),
    ("Septic absorption field rating", "USDA's soil-only rating of how well a drain field would work: not limited, somewhat limited, or very limited. It does not replace a site percolation test."),
    ("Annual average daily traffic", "PennDOT's count of vehicles per day on a state route, averaged over the year."),
    ("Garden / orchard / pasture ground", "Land classed for growing rather than building: by slope, hours of June sun, and whether the soil is wet. No setback is applied."),
]

LABELS = {"acres_computed": "Acres (mapped)", "acres_recorded": "Acres (deed)", "difference_pct": "Difference %",
          "share_of_property_pct": "Share of property %", "perimeter_ft": "Perimeter (ft)", "sqft_computed": "Sq ft",
          "parcel_acres": "Acres", "buildable_acres": "Buildable acres", "buildable_pct": "Buildable %",
          "steep_acres": "Steep acres", "approx_dims_ft": "Approx. size (ft)", "mean_slope_pct": "Mean slope %",
          "pad": "Pad", "parcel": "Parcel", "acres": "Acres", "pct": "% of property", "pct_of_property": "% of property",
          "outside_buildable_acres": "Acres outside buildable area", "jun21_sun_h_mean": "June 21 sun (h)",
          "mar21_sun_h_mean": "March 21 sun (h)", "dec21_sun_hours_mean": "Dec 21 sun (h)", "dec21_solar_index": "Winter solar index",
          "jun21_sun_hours_mean": "June 21 sun (h)", "south_or_flat_pct": "South-facing or flat %", "slope_class": "Slope",
          "class": "Class", "aspect": "Aspect", "contributing_acres": "Acres draining to this point",
          "musym": "Soil symbol", "muname": "Soil map unit", "hydgrp": "Hydrologic group", "drainagecl": "Drainage class",
          "hydricrating": "Hydric", "farmlndcl": "Farmland class", "Code": "Code", "Name": "District", "Type": "Type",
          "Municipali": "Municipality", "WebSite": "Ordinance", "long_code": "Code", "zoninggroup": "Group",
          "description": "Description", "DESCRIPTIO": "Description", "Category": "Category", "YRBLT": "Year built",
          "SFLA": "Living area (sq ft)", "STORIES": "Storeys", "address": "Address", "building_name": "Name",
          "approx_hgt": "Height (ft)", "square_ft": "Footprint (sq ft)", "road": "Road", "frontage_ft": "Frontage (ft)",
          "FLD_ZONE": "Flood zone", "WETLAND_TYPE": "Wetland type", "overlay_name": "Overlay", "overlay_na": "Overlay",
          "code_section": "Code section", "regulation": "Regulation"}


def fmt(v, col=""):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    c = col.lower()
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if float(v).is_integer() and ("year" in c or c in ("pad", "yrblt", "storeys", "stories")):
            return "" if v == 0 and c != "pad" else str(int(v))
        if "pct" in c or c.endswith("%") or "index" in c:
            return f"{v:,.1f}" if "index" not in c else f"{v:.2f}"
        if "acre" in c:
            return f"{v:,.3f}"
        if "ft" in c or "sq" in c or "height" in c or "area" in c or "($)" in c or "per day" in c:
            return f"{v:,.0f}"
        if "sun" in c or "(h)" in c:
            return f"{v:.1f}"
        return f"{v:,.3f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)
    s = str(v)
    return s[:-2] if s.endswith(".0") and s[:-2].isdigit() else s


def img(path, width=1400):
    if not path.exists():
        return ""
    im = Image.open(path).convert("RGB")
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82, optimize=True)
    return f'<img src="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}" alt="{html.escape(path.stem)}">'


def table(df, drop=(), rename=None):
    if df is None or len(df) == 0:
        return "<p class=small>none</p>"
    df = df.drop(columns=[c for c in drop if c in df.columns])
    cols = list(df.columns)
    labels = {**LABELS, **(rename or {})}
    num = {c for c in cols if pd.api.types.is_numeric_dtype(df[c])}
    head = "".join(f'<th class="{"num" if c in num else ""}">{html.escape(labels.get(c, c))}</th>' for c in cols)
    rows = "".join("<tr>" + "".join(f'<td class="{"num" if c in num else ""}">{html.escape(fmt(r[c], labels.get(c, c)))}</td>'
                                    for c in cols) + "</tr>" for _, r in df.iterrows())
    return f"<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>"


def csv(out, name):
    p = out / name
    return pd.read_csv(p, dtype={"PARCEL": str, "PARCELID": str}) if p.exists() else None


def card(value, label, cls=""):
    return f'<div class="card {cls}"><div class="v">{value}</div><div class="l">{label}</div></div>'


def pct_dict(d):
    return ", ".join(f"{k} {v:.1f}%" for k, v in d.items()) if d else ""


def main():
    cfg = load_config()
    out = cfg["_out"]
    E = json.loads((out / "evaluation.json").read_text())
    B, S, W, V, thr = E["buildable"], E["sun"], E["stormwater"], E["services"], E["thresholds"]
    Gr = E.get("growing") or {}
    idf = cfg["parcels"]["id_field"]
    labf = cfg["parcels"].get("label_field") or idf
    parcels = gpd.read_file(property_path(cfg), layer="parcels")
    boundary = gpd.read_file(property_path(cfg), layer="property_boundary")
    prop_acres = float(area_acres(boundary.geometry).iloc[0])      # vector total, used everywhere a total is printed
    parcels["_acres"] = area_acres(parcels.geometry)
    label = dict(zip(parcels[idf].astype(str), parcels[labf].astype(str)))
    order = parcels.sort_values(labf)[idf].astype(str).tolist()
    title = cfg.get("title") or cfg["name"].replace("_", " ").title()

    def with_address(df, col=idf):
        if df is None or col not in df.columns or any(c.lower() == "address" for c in df.columns if c != col):
            return df
        df = df.copy()
        df[col] = df[col].astype(str).str.replace(r"\.0$", "", regex=True)
        df.insert(list(df.columns).index(col) + 1, "Address", df[col].map(label))
        df["_o"] = df[col].map({k: i for i, k in enumerate(order)})
        return df.sort_values("_o").drop(columns="_o")

    # ---------------- key findings (capped), each a verdict word + one sentence
    flags = []
    bp = B["buildable_pct"]
    flags.append(("bad" if bp < 25 else "warn" if bp < 50 else "good",
                  f"{B['buildable_acres']:.1f} of {prop_acres:.1f} acres ({bp}%) is buildable at the "
                  f"{thr.get('max_build_slope_pct', 15)}% slope limit and {thr.get('property_line_setback_ft', 50)} ft setback; "
                  f"{B['buildable_if_slope_25_acres']:.1f} acres if slopes to 25% are accepted."))
    if B["pads"]:
        p0 = B["pads"][0]
        flags.append(("note", f"Largest building pad: {p0['acres']:.1f} acres, about {p0['approx_dims_ft']} ft, mean slope "
                              f"{p0['mean_slope_pct']}%, at {label.get(str(p0['parcel']), p0['parcel'])}."))
    else:
        flags.append(("warn", f"No contiguous buildable patch of {thr.get('min_building_pad_acres', 0.5)} acres; "
                              "the gentle ground is in small pieces or already holds the existing house."))
    if Gr:
        cult = Gr["garden_acres"] + Gr["orchard_acres"]
        flags.append(("good" if cult >= 1 else "warn" if cult >= 0.25 else "bad",
                      f"Growing: {Gr['garden_acres']:.1f} acres garden-grade, {Gr['orchard_acres']:.1f} acres orchard or terrace, "
                      f"{Gr['pasture_acres']:.1f} acres pasture; {Gr['usable_pct']}% of the property is usable for building, growing or grazing."))
        if Gr.get("canopy"):
            c = Gr["canopy"]
            flags.append(("warn" if c["canopy_pct_property"] > 50 else "note",
                          f"Tree canopy covers {c['canopy_pct_property']}% of the property, including {c['cultivable_under_canopy_acres']:.1f} acres of the growing ground; sun figures apply after clearing."))
    si, full = S.get("dec21_solar_index_buildable"), S["dec21_hours_at_flat_unshaded"]
    if si is not None:
        flags.append(("good" if si >= 0.9 else "warn" if si >= 0.6 else "bad",
                      f"Winter sun on the buildable ground: {S['dec21_sun_hours_buildable_mean']} of {full} possible hours on Dec 21, "
                      f"solar index {si} (1.0 = flat open ground; {S['south_or_flat_pct']}% of the site faces south or is flat). Terrain only; trees not modelled."))
    ro = W["runon_from_offsite_acres"]
    flags.append(("warn" if ro > prop_acres * 0.5 else "note",
                  f"{ro:.1f} acres of neighbouring land drain onto the property, with about {W['concentrated_flow_path_ft']:,.0f} ft of concentrated flow paths crossing it."))
    soils = W.get("soils") or {}
    if soils:
        gi = soils.get("good_infiltration_pct(A/B)", 0)
        flags.append(("good" if gi >= 60 else "warn" if gi >= 30 else "bad",
                      f"Soils: {pct_dict(soils['hydrologic_group_pct'])} by hydrologic group, so {gi:.0f}% absorbs rain well; "
                      f"hydric soil {soils.get('hydric_acres', 0):.1f} acres."))
    zspec = next((s for s in cfg.get("overlays") or [] if s.get("role") == "zoning"), None)
    if V.get("zoning") and zspec:
        z = V["zoning"][0]
        code = z.get(zspec.get("class_field"), "")
        desc = z.get(zspec.get("describe_field") or "", "")
        flags.append(("note", f"Zoning: {code}" + (f", {desc}" if desc and desc != code else "") + "."))
    for key, word, absent in (("sewer_pct", "Public sewer service area", "on-site septic likely"),
                              ("water_pct", "Public water service area", "a well would be needed")):
        v = V.get(key)
        if v is not None:
            cov = sum(v.values()) if v else 0
            flags.append(("good" if cov >= 95 else "warn" if cov > 0 else "bad",
                          f"{word} covers {cov:.0f}% of the property" + (f" ({', '.join(v)})." if v else f"; {absent}.")))
    R = E.get("restrictions") or {}
    if R.get("historic"):
        h = R["historic"][0]
        flags.append(("warn", f"{sum(r['pct'] for r in R['historic']):.0f}% of the property is inside a National Register historic "
                              f"{str(h.get('ResType', 'listing')).lower()}: {h.get('RESNAME', '')}. Exterior changes and demolition can face review."))
    if R.get("historic_local"):
        flags.append(("warn", f"Inside a local historic district: {R['historic_local'][0].get('name', '')}; local commission approval applies to exterior work."))
    if R.get("easements"):
        e = R["easements"][0]
        flags.append(("warn", f"A conservation easement touches the property ({e.get('sitename', '')}, held by {e.get('esmthldr', '')}, "
                              f"{sum(r['acres'] for r in R['easements']):.2f} ac). Check the deed for what it restricts."))
    if R.get("preserved_farmland"):
        flags.append(("warn", "Preserved farmland (agricultural conservation easement) on the property: development is restricted."))
    if R.get("septic") and R.get("sewer_coverage_pct") is not None and R["sewer_coverage_pct"] < 100:
        worst = max(R["septic"].items(), key=lambda kv: kv[1])
        flags.append(("bad" if worst[0] == "Very limited" else "warn",
                      f"Public sewer covers {R['sewer_coverage_pct']:.0f}% of the property; the soil survey rates most of the rest "
                      f"'{worst[0]}' for a septic absorption field, so on-lot sewage needs site testing."))
    if R.get("transmission"):
        t0 = R["transmission"][0]
        if t0["distance_ft"] <= 500:
            flags.append(("warn", f"Electric transmission line ({t0.get('Voltage', '')}) {t0['distance_ft']:,.0f} ft from the boundary."))
    if R.get("traffic"):
        t0 = R["traffic"][0]
        flags.append(("note", f"Adjoining state route SR {t0.get('ST_RT_NO')} carries about {int(t0.get('CUR_AADT') or 0):,} vehicles a day; "
                              "a new driveway onto it needs a PennDOT highway occupancy permit."))
    if R.get("taxes"):
        flags.append(("note", f"Assessed value ${R['taxes']['assessed_total']:,.0f}; estimated property tax ${R['taxes']['annual_total']:,.0f} a year."))
    if V.get("road_frontage"):
        flags.append(("note", "Road frontage: " + ", ".join(f"{r['road']} {r['frontage_ft']:,.0f} ft" for r in V["road_frontage"]) + "."))
    WORD = {"bad": "Risk", "warn": "Check", "good": "OK", "note": "Note"}
    flags_html = "".join(f'<li><span class="tag {c}">{WORD[c]}</span>{html.escape(t)}</li>' for c, t in flags[:14])

    # ---------------- cards
    cards = [card(f"{prop_acres:.1f} ac", "property, all parcels merged"),
             card(f"{B['buildable_acres']:.1f} ac", f"buildable at {thr.get('max_build_slope_pct', 15)}% slope", "bad" if bp < 25 else "warn" if bp < 50 else "good"),
             card(f"{bp}%", "of property buildable")]
    if Gr:
        cards += [card(f"{Gr['garden_acres']:.1f} ac", "garden-grade ground", "good" if Gr["garden_acres"] >= 1 else "warn"),
                  card(f"{Gr['usable_pct']}%", "usable to build, grow or graze")]
    if si is not None:
        cards.append(card(f"{si}", "winter solar index (1.0 = flat open ground)", "good" if si >= 0.9 else "warn" if si >= 0.6 else "bad"))
    cards.append(card(f"{ro:.1f} ac", "uphill land draining onto the site", "warn" if ro > prop_acres * 0.5 else ""))
    if soils:
        cards.append(card(f"{soils.get('good_infiltration_pct(A/B)', 0):.0f}%", "soils that absorb rain well (group A/B)"))
    if V.get("zoning") and zspec:
        cards.append(card(html.escape(str(V["zoning"][0].get(zspec.get("class_field"), ""))), "zoning"))

    # ---------------- buyer's reading from summary.md
    buyer = ""
    sm = out / "summary.md"
    if sm.exists():
        sec = sm.read_text().split("## Reading it as a buyer")
        if len(sec) > 1:
            paras = [p for p in sec[1].strip().split("\n\n") if p and not p.startswith("Numbers come")]
            buyer = '<div class="buyer"><h2>Reading it as a buyer</h2>' + "".join(f"<p>{html.escape(p.replace(chr(10), ' '))}</p>" for p in paras) + "</div>"

    # ---------------- sections
    meas = with_address(csv(out, "parcel_measurements.csv"))
    pads = pd.DataFrame(B["pads"])
    if len(pads):
        pads["parcel"] = pads["parcel"].astype(str).map(lambda x: label.get(x, x))
    build_parcel = with_address(csv(out, "buildable_by_parcel.csv"))
    if build_parcel is not None:  # vector acres for the parcel column, raster only for the buildable share
        build_parcel["parcel_acres"] = build_parcel[idf].map(dict(zip(parcels[idf].astype(str), parcels["_acres"]))).round(3)
    outl = pd.DataFrame(W["outlets"])
    if len(outl):
        outl["parcel"] = outl["parcel"].astype(str).map(lambda x: label.get(x, x))

    def overlay_spec(role):
        return next((s for s in cfg.get("overlays") or [] if s.get("role") == role), None)

    def overlay_table(spec, drop=()):
        """By-class table for an overlay plus explanations of its codes."""
        df = csv(out, f"overlay_{spec['name']}_by_class.csv")
        if df is None or len(df) == 0 or df["acres"].sum() == 0:
            return ""
        cls = spec.get("class_field")
        full = None
        try:
            full = gpd.read_file(out / "overlays.gpkg", layer=spec["name"])
        except Exception:  # noqa: BLE001
            pass
        if spec.get("role") == "soils" and full is not None and "muname" in full.columns:
            df = df.merge(full[["musym", "muname", "hydgrp", "drainagecl", "farmlndcl"]].drop_duplicates("musym"), on="musym", how="left")
            df = df[["musym", "muname", "hydgrp", "drainagecl", "farmlndcl", "acres", "pct_of_property"]]
        h = table(df, drop=drop)
        if cls and cls in df.columns:
            h += explain_html(spec, df[cls].tolist(), full)
        if spec.get("role") == "soils" and full is not None:
            for ttl, blk, col in (("Hydrologic group", "hydrologic_groups", "hydgrp"), ("Drainage class", "drainage_classes", "drainagecl")):
                if col in full.columns:
                    about, rows = block_rows(blk, full[col].dropna().tolist())
                    if rows:
                        h += f'<div class="defs"><b>{ttl}.</b> {html.escape(about)}<ul>' + "".join(f"<li><b>{html.escape(c)}</b>: {html.escape(t)}</li>" for c, t in rows) + "</ul></div>"
        return h

    def overlay_map(spec):
        p = out / f"map_overlay_{spec['name']}.png"
        return img(p) if p.exists() else ""

    parts = [f"<!DOCTYPE html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
             f"<title>Site evaluation: {html.escape(title)}</title><style>{CSS}</style></head><body>",
             f"<h1>{html.escape(title)}</h1>",
             f"<div class=sub>{len(parcels)} parcel{'s' if len(parcels) != 1 else ''}, {prop_acres:.3f} acres with all parcels merged. "
             f"Assumed and not yet checked against the municipal ordinance: slope limit {thr.get('max_build_slope_pct', 15)}%, "
             f"property-line setback {thr.get('property_line_setback_ft', 50)} ft, stream buffer {thr.get('stream_buffer_ft', 100)} ft, "
             f"wetland buffer {thr.get('wetland_buffer_ft', 50)} ft. Built from public data; verify with a survey before relying on it.</div>",
             (f"<p class=small><b>Listing notes:</b> {html.escape(str(cfg['notes']).strip())}</p>" if cfg.get("notes") else ""),
             "<div class=cards>" + "".join(cards) + "</div>",
             buyer,
             "<h2>Key findings</h2><ul class=flags>" + flags_html + "</ul>",
             "<h2>Parcels</h2>", img(out / "map_parcels.png"),
             table(meas, drop=("sqft_computed", "perimeter_ft")),
             "<h2>Buildable area</h2>",
             "<p class=small>Yellow passes every test; shaded areas show which constraint removes the rest. Black outlines are contiguous "
             "building pads. Existing houses are not excluded, so a pad can be where the house already stands.</p>",
             img(out / "map_buildable.png"),
             "<h3>Largest building pads</h3>" + table(pads),
             "<h3>By parcel</h3>" + table(build_parcel)]
    if Gr:
        t = Gr.get("thresholds", {})
        gc = csv(out, "growing_by_class.csv")
        parts += ["<h2>Growing ground</h2>",
                  f"<p class=small>Land classed for cultivation rather than construction, with no setback. Garden: slope at or below "
                  f"{t.get('garden_max_slope_pct', 8)}% with at least {t.get('garden_min_jun_sun_h', 8)} hours of June sun on dry soil. "
                  f"Orchard or terrace: slope to {t.get('orchard_max_slope_pct', 20)}%. Pasture: slope to {t.get('pasture_max_slope_pct', 25)}%. "
                  f"USDA prime farmland soil {Gr['prime_farmland_acres']:.2f} acres, farmland of statewide importance {Gr['statewide_importance_acres']:.2f} acres.</p>",
                  (f"<p class=small>A steep slope regulation covers {Gr['steep_slope_regulation']['regulated_pct_property']}% of the property, "
                   f"including {Gr['steep_slope_regulation']['cultivable_in_regulated_acres']:.2f} acres of the garden and orchard ground and "
                   f"{Gr['steep_slope_regulation']['pasture_in_regulated_acres']:.2f} acres of the pasture ground, so clearing or terracing there needs review "
                   f"and the usable figure is an upper bound.</p>" if Gr.get("steep_slope_regulation") else ""),
                  img(out / "map_growing.png"), table(gc), "<h3>By parcel</h3>" + table(with_address(csv(out, "growing_by_parcel.csv")))]
    parts += ["<h2>Sun</h2>",
              f"<p class=small>Hours of direct sun on Dec 21 from casting shadows across the elevation model (left), and the winter solar index, which also "
              f"accounts for the angle of the sun on the slope (right; 1.0 = flat open ground). Property averages: Dec 21 {S['dec21_sun_hours_property_mean']} h, "
              f"Mar 21 {S['mar21_sun_hours_property_mean']} h, Jun 21 {S['jun21_sun_hours_property_mean']} h, of {full} h possible on Dec 21. "
              f"Trees and neighbouring buildings are not modelled.</p>",
              img(out / "map_sun_dec21.png"), img(out / "map_solar_index_dec21.png"),
              "<h2>Water</h2>",
              f"<p class=small>Blue lines show where runoff concentrates on the natural ground; orange dots are where it leaves the property, labelled with the acres "
              f"draining there; magenta is ground that would pond. {ro:.2f} acres of uphill land drain onto the site; depressions that pond total "
              f"{W['ponding_acres']:.3f} acres. Pipes, ditches and culverts are not modelled.</p>",
              img(out / "map_stormwater.png"), "<h3>Where runoff leaves the property</h3>" + table(outl)]
    sspec = overlay_spec("soils")
    if sspec and soils:
        parts += ["<h3>Soils</h3>",
                  f"<p class=small>Hydrologic groups: {pct_dict(soils['hydrologic_group_pct'])}"
                  + (f"; on ground at or below 15% slope ({soils['gentle_ground_acres']:.2f} ac, where infiltration practices would go) "
                     f"{soils['good_infiltration_on_gentle_ground_pct']:.0f}% is group A or B" if "gentle_ground_acres" in soils else "")
                  + f". Hydric soil {soils['hydric_acres']:.3f} acres, poorly drained "
                  f"{soils['poorly_drained_acres']:.3f} acres, shallowest restrictive layer {soils['min_depth_to_restrictive_cm']} cm "
                  f"({(soils['min_depth_to_restrictive_cm'] or 0) / 30.48:.1f} ft) below the surface.</p>",
                  overlay_table(sspec), overlay_map(sspec)]
    parts += ["<h2>Zoning, services, access</h2>"]
    if zspec:
        zt = overlay_table(zspec, drop=("Type", "Map_Date", "pending"))
        if zt:
            parts += ["<h3>Zoning</h3>", zt, overlay_map(zspec)]
    for role, ttl in (("zoning_overlays", "Zoning overlays"), ("steep_slope_overlay", "Steep slope regulation"), ("floodplain", "Flood zones"), ("wetlands", "Wetlands")):
        sp = overlay_spec(role)
        if sp:
            t = overlay_table(sp)
            if t:
                parts += [f"<h3>{ttl}</h3>", t, overlay_map(sp)]
            else:
                parts.append(f"<p class=small>{html.escape(sp.get('description') or role)}: none on the property.</p>")
    svc_lines = []
    for key, word in (("sewer_pct", "Public sewer service area"), ("water_pct", "Public water service area")):
        v = V.get(key)
        if v is not None:
            svc_lines.append(f"{word}: " + (pct_dict(v) + " of the property" if v else "none mapped on the property"))
    if svc_lines:
        parts.append("<p>" + " &nbsp; ".join(html.escape(x) for x in svc_lines) + "</p>")
    if V.get("road_frontage"):
        parts += ["<h3>Road frontage</h3><p class=small>Boundary length within 40 ft of a street centerline.</p>", table(pd.DataFrame(V["road_frontage"]))]
    if V.get("buildings"):
        bdf = with_address(pd.DataFrame(V["buildings"]))
        parts += ["<h3>Existing structures</h3>", table(bdf)]
    # remaining overlays with features, by description
    done = {"soils", "zoning", "zoning_overlays", "steep_slope_overlay", "floodplain", "wetlands",
            "historic", "historic_local", "easements", "preserved_farmland", "transmission", "traffic", "school", "streams_dep"}
    none_list = []
    for sp in cfg.get("overlays") or []:
        if sp.get("role") in done:
            continue
        df = csv(out, f"overlay_{sp['name']}_by_class.csv")
        has = (df is not None and len(df) and df["acres"].sum() > 0)
        if not has:
            try:
                lyr = gpd.read_file(out / "overlays.gpkg", layer=sp["name"])
                has = len(lyr) > 0
            except Exception:  # noqa: BLE001
                has = False
        if has:
            parts += [f"<h3>{html.escape(sp.get('description') or sp['name'])}</h3>", overlay_table(sp) if df is not None else "", overlay_map(sp)]
        else:
            none_list.append(sp.get("description") or sp["name"])
    if none_list:
        parts.append("<p class=small>Layers with nothing on the property: " + "; ".join(html.escape(x) for x in none_list) + ".</p>")

    # ---------------- restrictions and context
    if R:
        def cov_rows(key, cols, labels_):
            rows = R.get(key)
            if not rows:
                return None
            df = pd.DataFrame(rows)
            df = df[[c for c in cols if c in df.columns] + ["acres", "pct"]]
            return table(df, rename=labels_)
        sec = ["<h2>Restrictions and context</h2>",
               "<p class=small>Designations, easements, utilities, traffic and taxes that restrict use or cost money. Coverage is the share of the property inside each feature.</p>"]
        for key, ttl, cols, labs, none in (
                ("historic", "National Register of Historic Places", ["RESNAME", "ResType", "CertDate", "NARA_URL"], {"RESNAME": "Listing", "ResType": "Type", "CertDate": "Listed", "NARA_URL": "Record"}, "none on the property"),
                ("historic_local", "Local historic district", ["name", "designated"], {"name": "District", "designated": "Designated"}, "none on the property"),
                ("easements", "Conservation easements", ["sitename", "esmthldr", "purpose", "duration", "pub_access"], {"sitename": "Site", "esmthldr": "Holder", "purpose": "Purpose", "duration": "Duration", "pub_access": "Public access"}, "none on the property"),
                ("preserved_farmland", "Preserved farmland", ["LOCATION1", "Municipali"], {"LOCATION1": "Farm", "Municipali": "Municipality"}, "none on the property"),
                ("school", "School district", ["Full_Name", "Web_URL"], {"Full_Name": "District", "Web_URL": "Website"}, "")):
            if R.get(key) is None:
                continue
            t = cov_rows(key, cols, labs)
            sec.append(f"<h3>{ttl}</h3>" + (t if t else f"<p class=small>{none}</p>" if none else ""))
        if R.get("transmission") is not None:
            sec.append("<h3>Electric transmission lines</h3>" + (table(pd.DataFrame(R["transmission"]), rename={"Voltage": "Voltage", "distance_ft": "Distance (ft)"}) if R["transmission"] else "<p class=small>none within the search area</p>"))
        if R.get("traffic") is not None:
            sec.append("<h3>Traffic on adjoining state routes</h3>" + (table(pd.DataFrame(R["traffic"]), rename={"ST_RT_NO": "State route", "CUR_AADT": "Vehicles per day", "TRK_PCT": "Trucks %", "BASE_YR_CL": "Count year"}) if R["traffic"] else "<p class=small>no state route within 100 ft of the boundary; local roads are not counted</p>"))
        if R.get("streams_dep"):
            s0 = R["streams_dep"][0]
            sec.append(f"<p>Nearest DEP-classified stream: {html.escape(str(s0.get('GNIS_NAME') or s0.get('SEGMENT_NA') or 'unnamed'))} "
                       f"({html.escape(str(s0.get('DES_USE_GE', '')))}, {html.escape(str(s0.get('USE_DESCRI', '')))}) at {s0['distance_ft']:,.0f} ft. "
                       "Pennsylvania protects High Quality and Exceptional Value streams with stricter permitting for earth disturbance.</p>")
        if R.get("septic"):
            sep = pd.DataFrame([{"rating": k_, "acres": v} for k_, v in sorted(R["septic"].items(), key=lambda kv: -kv[1])])
            bas = pd.DataFrame([{"rating": k_, "acres": v} for k_, v in sorted(R["basement"].items(), key=lambda kv: -kv[1])])
            sec += ["<h3>Soil suitability (USDA interpretations)</h3>",
                    f"<p class=small>Public sewer service area covers {R['sewer_coverage_pct'] if R.get('sewer_coverage_pct') is not None else 'n/a'}% of the property. "
                    "Where sewer is unavailable, on-lot sewage needs a site evaluation under Pennsylvania Act 537; these ratings describe the soil only.</p>",
                    "<div class=two><div><b>Septic absorption field</b>" + table(sep, rename={"rating": "Rating"}) + "</div><div><b>Dwelling with basement</b>" + table(bas, rename={"rating": "Rating"}) + "</div></div>"]
            about, rows = block_rows("ssurgo_ratings", list(R["septic"]) + list(R["basement"]))
            if rows:
                sec.append(f'<div class="defs"><b>What the ratings mean.</b> {html.escape(about)}<ul>' + "".join(f"<li><b>{html.escape(c)}</b>: {html.escape(t)}</li>" for c, t in rows) + "</ul></div>")
        if R.get("frost_free_days"):
            sec.append(f"<p>Frost-free growing season from the soil survey: {R['frost_free_days'][0]} to {R['frost_free_days'][1]} days.</p>")
        if R.get("taxes"):
            t = R["taxes"]
            tb = with_address(pd.DataFrame(t["by_parcel"]))
            sec += [f"<h3>Assessment and taxes</h3><p class=small>From the county assessment export. Assessed value ${t['assessed_total']:,.0f}; "
                    f"estimated annual tax ${t['annual_total']:,.0f} (county, municipal and school combined).</p>",
                    table(tb, rename={"annual_tax_estimate": "Annual tax estimate ($)", "assessed_value": "Assessed value ($)"})]
        parts += sec

    # ---------------- appendix
    parts += ["<h2>Appendix</h2>", "<h3>Slope classes</h3>", table(csv(out, "slope_by_class.csv")),
              "<h3>Aspect</h3>", table(csv(out, "aspect_classes.csv")),
              "<h3>Sun by parcel</h3>", table(with_address(csv(out, "sun_by_parcel.csv")))]
    src = out / "sources.md"
    if src.exists():
        rows = [l for l in src.read_text().splitlines() if l.startswith("|") and not l.startswith("|---")]
        if len(rows) > 1:
            df = pd.DataFrame([[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]],
                              columns=[c.strip() for c in rows[0].strip("|").split("|")])
            parts += ["<h3>Data sources</h3>", table(df)]
    parts += ["<h3>Glossary</h3><dl class=gloss>" + "".join(f"<dt>{html.escape(k)}</dt><dd>{html.escape(v)}</dd>" for k, v in GLOSSARY) + "</dl>",
              "</body></html>"]
    outp = out / "report.html"
    outp.write_text("\n".join(p for p in parts if p))
    print(f"wrote {outp.relative_to(cfg['_root'])} ({outp.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
