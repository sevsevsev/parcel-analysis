"""Plain-language explanations for codes that appear in layer tables."""
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
_DEFS = None


def defs():
    global _DEFS
    if _DEFS is None:
        p = ROOT / "definitions.yaml"
        _DEFS = yaml.safe_load(open(p)) if p.exists() else {}
    return _DEFS


def decode_nwi(code: str):
    """Decode a Cowardin code like PFO1A or PEM1Cx into words."""
    d = defs()
    if not isinstance(code, str) or len(code) < 3:
        return None
    parts = [d.get("nwi_system", {}).get(code[0], code[0]).split(",")[0].lower()]
    cls = code[1:3]
    parts.append(d.get("nwi_class", {}).get(cls, cls).split(",")[0].lower())
    rest = code[3:]
    rest = rest.lstrip("0123456789")  # subclass digit
    if rest:
        reg = d.get("nwi_regime", {}).get(rest[0])
        if reg:
            parts.append(reg.split(",")[0].lower())
        for m in rest[1:]:
            mm = d.get("nwi_modifier", {}).get(m)
            if mm:
                parts.append(mm.rstrip(".").lower())
    return ", ".join(parts)


def explain(spec: dict, values, df: pd.DataFrame = None):
    """Return (about_text, [(code, description), ...]) for the codes in `values` of a layer spec.

    Sources: the spec's `codes:` key naming a definitions.yaml block; the spec's `describe_field`
    (a column in df holding the long name for each code); NWI attribute decoding for role wetlands.
    """
    d = defs()
    about, rows, seen = "", [], set()
    block = d.get(spec.get("codes") or "", {}) if spec.get("codes") else {}
    if block:
        about = block.get("_about", "")
    desc_field, cls = spec.get("describe_field"), spec.get("class_field")
    for v in values:
        if v is None or (isinstance(v, float) and pd.isna(v)) or str(v) in seen:
            continue
        seen.add(str(v))
        text = block.get(str(v)) if block else None
        if text is None and desc_field and df is not None and desc_field in df.columns and cls in df.columns:
            m = df[df[cls].astype(str) == str(v)]
            if len(m):
                vals = [str(x) for x in m[desc_field].dropna().unique() if str(x).strip()]
                text = "; ".join(vals[:3]) if vals else None
        if text is None and spec.get("role") == "wetlands":
            text = decode_nwi(str(v))
        if text:
            rows.append((str(v), text))
    return about, rows


def explain_md(spec, values, df=None, title="What the codes mean"):
    about, rows = explain(spec, values, df)
    if not rows and not about:
        return ""
    out = [f"**{title}.**" + (f" {about}" if about else ""), ""]
    out += [f"- **{c}**: {t}" for c, t in rows]
    return "\n".join(out) + "\n"


def explain_html(spec, values, df=None, title="What the codes mean"):
    import html as H
    about, rows = explain(spec, values, df)
    if not rows and not about:
        return ""
    items = "".join(f"<li><b>{H.escape(c)}</b>: {H.escape(t)}</li>" for c, t in rows)
    return (f'<div class="defs"><b>{H.escape(title)}.</b> {H.escape(about)}<ul>{items}</ul></div>')


def extra_blocks(spec):
    """Other definition blocks a layer's table uses (e.g. soils tables show hydgrp and drainagecl)."""
    role = spec.get("role")
    if role == "soils":
        return [("Hydrologic group", "hydrologic_groups"), ("Drainage class", "drainage_classes"),
                ("Farmland class", "farmland_classes")]
    return []


def block_rows(name, values):
    d = defs().get(name, {})
    rows = [(str(v), d[str(v)]) for v in dict.fromkeys(values) if str(v) in d]
    return d.get("_about", ""), rows
