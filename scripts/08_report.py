"""Self-contained HTML report for a listing: scorecard, key findings, maps and tables.
Everything (images included) is embedded so the file can be emailed or opened anywhere."""
import base64
import html
import io
import json
import sys
from pathlib import Path

from PIL import Image

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from _common import load_config  # noqa: E402

CSS = """
:root{--bg:#fff;--fg:#1a1a1a;--muted:#666;--line:#e3e3e3;--accent:#b45309;--good:#1a7f37;--warn:#b45309;--bad:#b91c1c;--card:#fafaf7}
@media(prefers-color-scheme:dark){:root{--bg:#141414;--fg:#eee;--muted:#aaa;--line:#333;--card:#1e1e1c}}
body{font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--fg);margin:0;padding:24px 16px;max-width:1100px;margin-inline:auto}
h1{font-size:26px;margin:0 0 4px}h2{font-size:20px;margin:36px 0 10px;border-bottom:1px solid var(--line);padding-bottom:4px}h3{font-size:16px;margin:20px 0 6px}
.sub{color:var(--muted);margin-bottom:20px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:16px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.card .v{font-size:26px;font-weight:650;line-height:1.1}.card .l{color:var(--muted);font-size:13px;margin-top:4px}
.card.good .v{color:var(--good)}.card.warn .v{color:var(--warn)}.card.bad .v{color:var(--bad)}
table{border-collapse:collapse;width:100%;font-size:13.5px;margin:8px 0 16px}th,td{border-bottom:1px solid var(--line);padding:5px 8px;text-align:left;vertical-align:top}th{background:var(--card)}td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:8px;margin:6px 0 14px}
ul.flags li{margin:4px 0}.flag-bad::before{content:"\\26A0  ";color:var(--bad)}.flag-good::before{content:"\\2713  ";color:var(--good)}.flag-note::before{content:"\\2139  ";color:var(--muted)}.flag-warn::before{content:"\\26A0  ";color:var(--warn)}
.small{font-size:13px;color:var(--muted)}
"""


def img(path, width=1400):
    """Embed a figure, downscaled to `width` px and JPEG-compressed to keep the report small."""
    if not path.exists():
        return ""
    im = Image.open(path).convert("RGB")
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82, optimize=True)
    b = base64.b64encode(buf.getvalue()).decode()
    return f'<img src="data:image/jpeg;base64,{b}" alt="{html.escape(path.stem)}">'


def table(df: pd.DataFrame):
    if df is None or len(df) == 0:
        return "<p class=small>none</p>"
    num = {c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])}
    head = "".join(f'<th class="{"num" if c in num else ""}">{html.escape(str(c))}</th>' for c in df.columns)
    rows = []
    for _, r in df.iterrows():
        cells = "".join(f'<td class="{"num" if c in num else ""}">{html.escape("" if pd.isna(r[c]) else str(r[c]))}</td>'
                        for c in df.columns)
        rows.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def csv(out, name):
    p = out / name
    return pd.read_csv(p) if p.exists() else None


def card(value, label, cls=""):
    return f'<div class="card {cls}"><div class="v">{value}</div><div class="l">{label}</div></div>'


def main():
    cfg = load_config()
    out = cfg["_out"]
    ev_path = out / "evaluation.json"
    if not ev_path.exists():
        sys.exit("run scripts/07_site_evaluation.py first")
    E = json.loads(ev_path.read_text())
    B, S, W, V = E["buildable"], E["sun"], E["stormwater"], E["services"]
    Gr = E.get("growing") or {}
    thr = E["thresholds"]
    measurements = csv(out, "parcel_measurements.csv")
    idf = cfg["parcels"]["id_field"]
    lab = cfg["parcels"].get("label_field")

    # flags: plain-language findings a buyer should notice
    flags = []
    bp = B["buildable_pct"]
    flags.append(("bad" if bp < 25 else "warn" if bp < 50 else "good",
                  f"{B['buildable_acres']:.1f} of {B['property_acres']:.1f} acres ({bp}%) is buildable at the "
                  f"{thr.get('max_build_slope_pct', 15)}% slope limit; {B['buildable_if_slope_25_acres']:.1f} acres if 25% slopes are accepted."))
    if B["pads"]:
        p0 = B["pads"][0]
        flags.append(("note", f"Largest contiguous building pad: {p0['acres']:.1f} acres, roughly {p0['approx_dims_ft']} ft, "
                              f"mean slope {p0['mean_slope_pct']}%, on parcel {p0['parcel']}."))
    else:
        flags.append(("bad", f"No contiguous buildable patch of {thr.get('min_building_pad_acres', 0.5)} acres or more."))
    rb = B["removed_by"]
    big = {k: v for k, v in rb.items() if v > 0.05}
    if big:
        flags.append(("note", "Constraints removing area: " + ", ".join(f"{k.replace('_', ' ')} {v:.1f} ac" for k, v in big.items()) + "."))
    ds = S["dec21_sun_hours_buildable_mean"]
    full = S["dec21_hours_at_flat_unshaded"]
    if ds is not None:
        flags.append(("good" if ds >= 0.75 * full else "warn" if ds >= 0.5 * full else "bad",
                      f"Winter sun on the buildable ground averages {ds} h of a possible {full} h on Dec 21 (terrain shading only; trees not modelled)."))
    si = S.get("dec21_solar_index_buildable")
    if si is not None:
        flags.append(("good" if si >= 0.9 else "warn" if si >= 0.6 else "bad",
                      f"Winter solar index on buildable ground is {si} (1.0 = flat open ground; south slopes exceed 1, north slopes fall below)."))
    flags.append(("note", f"{S['south_or_flat_pct']}% of the property faces south-east to south-west or is flat."))
    if Gr:
        flags.append(("good" if Gr["garden_acres"] >= 1 else "warn" if Gr["garden_acres"] >= 0.25 else "bad",
                      f"{Gr['garden_acres']:.1f} acres are garden-grade ground (gentle, sunny, dry soil), "
                      f"{Gr['orchard_acres']:.1f} acres suit orchards or terraces and {Gr['pasture_acres']:.1f} acres pasture. "
                      f"{Gr['cultivable_outside_buildable_acres']:.1f} acres of that lie outside the buildable area, so they are not lost to the building analysis."))
        if Gr["prime_farmland_acres"] > 0.1 or Gr["statewide_importance_acres"] > 0.1:
            flags.append(("good", f"USDA rates {Gr['prime_farmland_acres']:.1f} acres as prime farmland soil and "
                                  f"{Gr['statewide_importance_acres']:.1f} acres as farmland of statewide importance."))
        flags.append(("note", f"Usable for building, growing or grazing combined: {Gr['usable_acres_build_or_grow_or_graze']:.1f} acres ({Gr['usable_pct']}%)."))
        if Gr.get("canopy"):
            c = Gr["canopy"]
            flags.append(("warn" if c["canopy_pct_property"] > 50 else "note",
                          f"Mapped tree canopy covers {c['canopy_pct_property']}% of the property; {c['buildable_under_canopy_acres']:.1f} acres of "
                          f"buildable and {c['cultivable_under_canopy_acres']:.1f} acres of growing ground are under trees today."))
    ro = W["runon_from_offsite_acres"]
    flags.append(("warn" if ro > B["property_acres"] * 0.5 else "note",
                  f"{ro:.1f} acres of neighbouring land drains onto the property; "
                  f"about {W['concentrated_flow_path_ft']:.0f} ft of concentrated flow paths cross it."))
    soils = W.get("soils") or {}
    if soils:
        gi = soils.get("good_infiltration_pct(A/B)", 0)
        flags.append(("good" if gi >= 60 else "warn" if gi >= 30 else "bad",
                      f"{gi}% of the soils are hydrologic group A/B (infiltrate well); hydric soils {soils.get('hydric_acres', 0):.1f} ac."))
    if V.get("zoning"):
        z = V["zoning"][0]
        flags.append(("note", f"Zoning: {z.get('Name', z.get('Code'))} ({z.get('Municipali', '')})."))
    sw = V.get("sewer_pct")
    if sw is not None:
        cov = sum(sw.values()) if sw else 0
        flags.append(("good" if cov >= 95 else "warn" if cov > 0 else "bad",
                      f"Public sewer service area covers {cov:.0f}% of the property" + (f" ({', '.join(sw)})." if sw else ": on-site septic likely.")))
    wt = V.get("water_pct")
    if wt is not None:
        cov = sum(wt.values()) if wt else 0
        flags.append(("good" if cov >= 95 else "warn" if cov > 0 else "bad",
                      f"Public water service area covers {cov:.0f}% of the property" + (f" ({', '.join(wt)})." if wt else ": well needed.")))
    if V.get("road_frontage"):
        flags.append(("note", "Road frontage: " + ", ".join(f"{r['road']} {r['frontage_ft']:.0f} ft" for r in V["road_frontage"]) + "."))
    if V.get("buildings"):
        flags.append(("note", f"{len(V['buildings'])} existing structures on the parcels (see table)."))

    cards = [card(f"{B['property_acres']:.1f} ac", "property (dissolved)"),
             card(f"{B['buildable_acres']:.1f} ac", f"buildable at {thr.get('max_build_slope_pct', 15)}% slope",
                  "bad" if bp < 25 else "warn" if bp < 50 else "good"),
             card(f"{bp}%", "of property buildable"),
             card(f"{ds if ds is not None else '-'} h", f"Dec 21 sun on buildable ground (max {full})",
                  "" if ds is None else "good" if ds >= 0.75 * full else "warn"),
             card(f"{S.get('dec21_solar_index_buildable', '-')}", "winter solar index (1 = flat)",
                  "" if S.get("dec21_solar_index_buildable") is None else "good" if S["dec21_solar_index_buildable"] >= 0.9 else "warn" if S["dec21_solar_index_buildable"] >= 0.6 else "bad"),
             card(f"{Gr['garden_acres']:.1f} ac", "garden-grade ground", "good" if Gr.get("garden_acres", 0) >= 1 else "warn") if Gr else "",
             card(f"{Gr['usable_pct']}%", "usable: build, grow or graze") if Gr else "",
             card(f"{ro:.1f} ac", "off-site run-on", "warn" if ro > B["property_acres"] * 0.5 else ""),
             card(f"{soils.get('good_infiltration_pct(A/B)', '-')}%", "soils in group A/B") if soils else ""]
    if V.get("zoning"):
        cards.append(card(html.escape(str(V["zoning"][0].get("Code", ""))), "zoning"))

    def sec_table(name, df_or_records):
        df = pd.DataFrame(df_or_records) if isinstance(df_or_records, list) else df_or_records
        return f"<h3>{name}</h3>{table(df)}"

    parts = [f"<!DOCTYPE html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
             f"<title>Site evaluation: {html.escape(cfg['name'])}</title><style>{CSS}</style></head><body>",
             f"<h1>Site evaluation: {html.escape(cfg['name'])}</h1>",
             f"<div class=sub>{len(measurements) if measurements is not None else ''} parcels, {B['property_acres']:.3f} acres. "
             f"Thresholds: slope &le; {thr.get('max_build_slope_pct', 15)}%, setback {thr.get('property_line_setback_ft', 50)} ft, "
             f"stream buffer {thr.get('stream_buffer_ft', 100)} ft, wetland buffer {thr.get('wetland_buffer_ft', 50)} ft. "
             f"Generated from public data; verify with a survey and the municipal ordinance before relying on it.</div>",
             "<div class=cards>" + "".join(cards) + "</div>",
             (f"<p class=small><b>Listing notes:</b> {html.escape(str(cfg['notes']).strip())}</p>" if cfg.get("notes") else ""),
             "<h2>Key findings</h2><ul class=flags>" + "".join(f'<li class="flag-{c}">{html.escape(t)}</li>' for c, t in flags) + "</ul>",
             "<h2>Parcels</h2>", img(out / "map_parcels.png"), table(measurements),
             "<h2>Buildable area</h2>", img(out / "map_buildable.png"),
             sec_table("Largest contiguous building pads", B["pads"]), sec_table("By parcel", csv(out, "buildable_by_parcel.csv")),
             "<h2>Terrain</h2>", img(out / "map_slope.png"), sec_table("Slope classes", csv(out, "slope_by_class.csv")),
             "<h2>Sun exposure</h2>",
             f"<p class=small>Direct sun hours computed by casting shadows across the bare-earth DEM for Dec 21, Mar 21 and Jun 21 "
             f"at latitude {S['latitude']}. Property mean: Dec {S['dec21_sun_hours_property_mean']} h, Mar {S['mar21_sun_hours_property_mean']} h, "
             f"Jun {S['jun21_sun_hours_property_mean']} h. Tree canopy and buildings are not modelled, so treat this as an upper bound.</p>",
             img(out / "map_sun_dec21.png"), img(out / "map_solar_index_dec21.png"), sec_table("Aspect", csv(out, "aspect_classes.csv")), sec_table("By parcel", csv(out, "sun_by_parcel.csv")),
             "<h2>Stormwater</h2>",
             f"<p class=small>D8 flow routing on the DEM. Run-on {ro:.2f} ac; ponding depressions {W['ponding_acres']:.3f} ac; "
             f"concentrated flow (&ge; {W['flow_path_threshold_acres']} ac contributing) about {W['concentrated_flow_path_ft']:.0f} ft.</p>",
             img(out / "map_stormwater.png"), sec_table("Where runoff leaves the property", W["outlets"])]
    if soils:
        parts += [f"<h3>Soils</h3><p class=small>Hydrologic groups: {html.escape(str(soils['hydrologic_group_pct']))}. "
                  f"Hydric {soils['hydric_acres']:.3f} ac, poorly drained {soils['poorly_drained_acres']:.3f} ac, "
                  f"shallowest restrictive layer {soils['min_depth_to_restrictive_cm']} cm.</p>",
                  img(out / "map_overlay_ssurgo_soils.png"), table(csv(out, "overlay_ssurgo_soils_by_class.csv"))]
    if Gr:
        t = Gr.get("thresholds", {})
        parts += ["<h2>Growing ground</h2>",
                  f"<p class=small>Where food could be grown, judged on slope, June 21 sun (terrain shading only) and soil wetness, "
                  f"without the building setback. Garden: slope &le; {t.get('garden_max_slope_pct', 8)}%, &ge; {t.get('garden_min_jun_sun_h', 8)} h sun. "
                  f"Orchard / terrace: slope &le; {t.get('orchard_max_slope_pct', 20)}%. Pasture: slope &le; {t.get('pasture_max_slope_pct', 25)}%. "
                  f"Wet ground is poorly drained or hydric soil or mapped wetland. Prime farmland {Gr['prime_farmland_acres']:.2f} ac, "
                  f"statewide importance {Gr['statewide_importance_acres']:.2f} ac.</p>",
                  img(out / "map_growing.png"), sec_table("By class", csv(out, "growing_by_class.csv")),
                  sec_table("By parcel", csv(out, "growing_by_parcel.csv"))]
    parts += ["<h2>Zoning, services, access</h2>"]
    if V.get("zoning"):
        parts.append(sec_table("Zoning", V["zoning"]))
    parts.append(f"<p>Public sewer service areas: {html.escape(str(V.get('sewer_pct')))} &nbsp; Public water: {html.escape(str(V.get('water_pct')))}</p>")
    if V.get("road_frontage"):
        parts.append(sec_table("Road frontage", V["road_frontage"]))
    if V.get("buildings"):
        parts.append(sec_table("Existing buildings", V["buildings"]))
    for name in ("map_overlay_montco_zoning.png", "map_overlay_fema_flood.png", "map_overlay_nwi_wetlands.png"):
        parts.append(img(out / name))
    src = out / "sources.md"
    if src.exists():
        rows = [l for l in src.read_text().splitlines() if l.startswith("|") and not l.startswith("|---")]
        if len(rows) > 1:
            df = pd.DataFrame([[c.strip() for c in r.strip("|").split("|")] for r in rows[1:]],
                              columns=[c.strip() for c in rows[0].strip("|").split("|")])
            parts += ["<h2>Data sources</h2>", table(df)]
    parts.append("</body></html>")
    outp = out / "report.html"
    outp.write_text("\n".join(parts))
    print(f"wrote {outp.relative_to(cfg['_root'])} ({outp.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
