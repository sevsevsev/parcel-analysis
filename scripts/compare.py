"""Side-by-side comparison of every evaluated listing: outputs/compare.md and compare.csv."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    rows = []
    for p in sorted(ROOT.glob("outputs/*/evaluation.json")):
        E = json.loads(p.read_text())
        B, S, W, V = E["buildable"], E["sun"], E["stormwater"], E["services"]
        soils = W.get("soils") or {}
        rows.append({
            "listing": E["listing"],
            "acres": B["property_acres"],
            "buildable_acres": B["buildable_acres"],
            "buildable_pct": B["buildable_pct"],
            "largest_pad_acres": B["pads"][0]["acres"] if B["pads"] else 0,
            "dec21_sun_h_buildable": S["dec21_sun_hours_buildable_mean"],
            "winter_solar_index": S.get("dec21_solar_index_buildable"),
            "south_or_flat_pct": S["south_or_flat_pct"],
            "garden_acres": (E.get("growing") or {}).get("garden_acres"),
            "orchard_acres": (E.get("growing") or {}).get("orchard_acres"),
            "usable_pct": (E.get("growing") or {}).get("usable_pct"),
            "prime_farmland_acres": (E.get("growing") or {}).get("prime_farmland_acres"),
            "runon_acres": W["runon_from_offsite_acres"],
            "soils_AB_pct": soils.get("good_infiltration_pct(A/B)"),
            "hydric_acres": soils.get("hydric_acres"),
            "zoning": ", ".join(sorted({str(next((z[k] for k in ("Code", "ZONE", "zone") if k in z),
                                                 next(iter(z.values()), "")))
                                        for z in V.get("zoning", [])})),
            "sewer_pct": round(sum((V.get("sewer_pct") or {}).values()), 0) if V.get("sewer_pct") is not None else None,
            "water_pct": round(sum((V.get("water_pct") or {}).values()), 0) if V.get("water_pct") is not None else None,
            "frontage_ft": round(sum(r["frontage_ft"] for r in V.get("road_frontage", [])), 0),
            "buildings": len(V.get("buildings", [])),
            "historic_pct": round(sum(r["pct"] for r in (E.get("restrictions") or {}).get("historic") or []), 1),
            "easement_acres": round(sum(r["acres"] for r in (E.get("restrictions") or {}).get("easements") or []), 3),
            "annual_tax_est": ((E.get("restrictions") or {}).get("taxes") or {}).get("annual_total"),
        })
    if not rows:
        print("no evaluated listings yet")
        return
    df = pd.DataFrame(rows)
    (ROOT / "outputs").mkdir(exist_ok=True)
    df.to_csv(ROOT / "outputs" / "compare.csv", index=False)
    md = "# Listing comparison\n\n" + df.to_markdown(index=False) + "\n"
    (ROOT / "outputs" / "compare.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
