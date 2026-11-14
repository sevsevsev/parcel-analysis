"""FastAPI server: geocode, parcel picker, listings and jobs. Run: uvicorn app.server:app --port 8000"""
from __future__ import annotations

import json
import secrets
import sqlite3
import threading
import time
import traceback
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import geo, pipeline, registry

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "web.sqlite"
STATIC = ROOT / "app" / "static"
(ROOT / "listings" / "web").mkdir(parents=True, exist_ok=True)
(ROOT / "outputs" / "web").mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Parcel analysis")


# ----------------------------------------------------------------------------- storage
def db():
    con = sqlite3.connect(DB, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


with db() as con:
    con.executescript("""
    CREATE TABLE IF NOT EXISTS listings(id TEXT PRIMARY KEY, title TEXT, county_fips TEXT, parcel_ids TEXT, layers TEXT,
                                        created_at TEXT, status TEXT, config_path TEXT);
    CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, listing_id TEXT, status TEXT, step TEXT, steps_done INT, steps_total INT,
                                    log TEXT, error TEXT, created_at TEXT, pdf INT);
    """)

_queue: deque[str] = deque()
_logs: dict[str, deque] = {}
_wake = threading.Event()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def worker():
    while True:
        _wake.wait(timeout=2)
        _wake.clear()
        while _queue:
            job_id = _queue.popleft()
            try:
                run_job(job_id)
            except BaseException as e:  # noqa: BLE001
                with db() as con:
                    con.execute("UPDATE jobs SET status='failed', error=? WHERE id=?", (f"worker error: {e}", job_id))


def run_job(job_id: str):
    with db() as con:
        job = con.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        lst = con.execute("SELECT * FROM listings WHERE id=?", (job["listing_id"],)).fetchone()
    log = _logs.setdefault(job_id, deque(maxlen=400))

    def progress(step, i, n):
        with db() as con:
            con.execute("UPDATE jobs SET status=?, step=?, steps_done=?, steps_total=? WHERE id=?",
                        ("running" if step != "done" else "done", step, i, n, job_id))

    def logline(line):
        log.append(line)

    try:
        with db() as con:
            con.execute("UPDATE listings SET status='running' WHERE id=?", (lst["id"],))
        pipeline.run_listing(Path(lst["config_path"]), progress, logline, pdf=bool(job["pdf"]))
        with db() as con:
            con.execute("UPDATE jobs SET status='done', log=? WHERE id=?", ("\n".join(log), job_id))
            con.execute("UPDATE listings SET status='done' WHERE id=?", (lst["id"],))
    except BaseException as e:  # noqa: BLE001  the scripts call sys.exit() on fatal problems; that must fail the job, not kill the worker
        err = f"{type(e).__name__}: {e}" if not isinstance(e, SystemExit) else f"step stopped: {e}"
        log.append(err)
        log.append(traceback.format_exc()[-1500:])
        with db() as con:
            con.execute("UPDATE jobs SET status='failed', error=?, log=? WHERE id=?", (err, "\n".join(log), job_id))
            con.execute("UPDATE listings SET status='failed' WHERE id=?", (lst["id"],))


threading.Thread(target=worker, daemon=True).start()


# ----------------------------------------------------------------------------- models
class ListingIn(BaseModel):
    county_fips: str
    parcel_ids: list[str]
    title: str | None = None
    layers: list[str] | None = None
    thresholds: dict | None = None
    growing: dict | None = None
    pdf: bool = False


class RerunIn(BaseModel):
    layers: list[str] | None = None
    thresholds: dict | None = None
    growing: dict | None = None
    pdf: bool = False


# ----------------------------------------------------------------------------- lookups
@app.get("/api/geocode")
def api_geocode(q: str):
    try:
        g = geo.geocode(q)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"geocoder error: {e}")
    if not g:
        raise HTTPException(404, "no match for that address")
    return g


@app.get("/api/parcel")
def api_parcel(lat: float, lon: float, county_fips: str | None = None, nearest: int = 1):
    """Parcel under a point; with nearest=1 (default) falls back to the closest parcel within 40 m,
    which is what a geocoded address needs. Map clicks pass nearest=0 so a click on the road adds nothing."""
    try:
        p = geo.parcel_at(lat, lon, county_fips, radius_m=40.0 if nearest else 0)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"parcel service error: {e}")
    if not p:
        raise HTTPException(404, "no parcel at that point, or county not supported")
    return p


@app.get("/api/counties")
def api_counties():
    reg = registry.counties()
    return [{"fips": f, "name": c["name"], "layers": registry.layer_info(f)} for f, c in reg["counties"].items()]


@app.get("/api/presets")
def api_presets(county_fips: str | None = None):
    if county_fips:
        return registry.presets_for(county_fips)
    return {p: p for p in registry.PRESETS}


# ----------------------------------------------------------------------------- listings
def _summary(out: Path):
    ej = out / "evaluation.json"
    if not ej.exists():
        return None
    E = json.loads(ej.read_text())
    B, S, W, V, G, R = E["buildable"], E["sun"], E["stormwater"], E["services"], E.get("growing") or {}, E.get("restrictions") or {}
    zspec_code = ""
    if V.get("zoning"):
        z = V["zoning"][0]
        zspec_code = str(next((z[k] for k in ("Code", "long_code", "ZoningAbbr", "ZONE") if k in z), next(iter(z.values()), "")))
    return {"property_acres": B["property_acres"], "buildable_acres": B["buildable_acres"], "buildable_pct": B["buildable_pct"],
            "largest_pad_acres": B["pads"][0]["acres"] if B["pads"] else 0,
            "garden_acres": G.get("garden_acres"), "orchard_acres": G.get("orchard_acres"), "usable_pct": G.get("usable_pct"),
            "dec21_solar_index_buildable": S.get("dec21_solar_index_buildable"), "dec21_sun_hours_buildable": S.get("dec21_sun_hours_buildable_mean"),
            "runon_acres": W["runon_from_offsite_acres"], "soils_AB_pct": (W.get("soils") or {}).get("good_infiltration_pct(A/B)"),
            "zoning": zspec_code, "historic_pct": round(sum(r["pct"] for r in R.get("historic") or []), 1),
            "sewer_pct": round(sum((V.get("sewer_pct") or {}).values()), 0) if V.get("sewer_pct") is not None else None,
            "annual_tax_est": (R.get("taxes") or {}).get("annual_total")}


def _listing_row(row, with_geo=False):
    out = ROOT / "outputs" / "web" / row["id"]
    files = {"report": f"/api/listings/{row['id']}/report" if (out / "report.html").exists() else None,
             "atlas": f"/api/listings/{row['id']}/atlas.pdf" if (out / "evaluation.json").exists() else None,
             "evaluation_json": f"/api/listings/{row['id']}/files/evaluation.json" if (out / "evaluation.json").exists() else None,
             "property_gpkg": f"/api/listings/{row['id']}/files/property.gpkg" if (out / "property.gpkg").exists() else None,
             "evaluation_gpkg": f"/api/listings/{row['id']}/files/evaluation.gpkg" if (out / "evaluation.gpkg").exists() else None,
             "summary_md": f"/api/listings/{row['id']}/files/evaluation.md" if (out / "evaluation.md").exists() else None}
    with db() as con:
        j = con.execute("SELECT id, error FROM jobs WHERE listing_id=? ORDER BY created_at DESC LIMIT 1", (row["id"],)).fetchone()
    d = {"listing_id": row["id"], "title": row["title"], "county_fips": row["county_fips"], "parcel_ids": json.loads(row["parcel_ids"]),
         "layers": json.loads(row["layers"]), "created_at": row["created_at"], "status": row["status"],
         "job_id": j["id"] if j else None, "error": j["error"] if j else None,
         "summary": _summary(out), "files": files}
    if with_geo and (out / "property.gpkg").exists():
        try:
            import geopandas as gpd
            g = gpd.read_file(out / "property.gpkg", layer="parcels").to_crs(4326)
            d["parcels_geojson"] = json.loads(g.to_json())
        except Exception:  # noqa: BLE001
            pass
    return d


def _enqueue(listing_id: str, pdf: bool) -> str:
    job_id = "j_" + secrets.token_hex(6)
    with db() as con:
        con.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?)", (job_id, listing_id, "queued", None, 0, 0, "", None, now(), int(pdf)))
        con.execute("UPDATE listings SET status='queued' WHERE id=?", (listing_id,))
    _queue.append(job_id)
    _wake.set()
    return job_id


@app.post("/api/listings")
def api_create_listing(body: ListingIn):
    if not body.parcel_ids:
        raise HTTPException(400, "pick at least one parcel")
    if not registry.county(body.county_fips):
        raise HTTPException(400, "county not supported")
    listing_id = secrets.token_hex(4)
    layers = body.layers if body.layers is not None else registry.presets_for(body.county_fips)["build"]
    cfg = registry.build_listing_config(listing_id, body.county_fips, body.parcel_ids, layers, body.thresholds, body.growing, body.title)
    path = ROOT / "listings" / "web" / f"{listing_id}.yaml"
    path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    with db() as con:
        con.execute("INSERT INTO listings VALUES (?,?,?,?,?,?,?,?)",
                    (listing_id, cfg["title"], body.county_fips, json.dumps(body.parcel_ids), json.dumps(layers), now(), "queued", str(path)))
    job_id = _enqueue(listing_id, body.pdf)
    return {"listing_id": listing_id, "job_id": job_id, "url": f"/listing/{listing_id}"}


@app.post("/api/listings/{listing_id}/rerun")
def api_rerun(listing_id: str, body: RerunIn):
    with db() as con:
        row = con.execute("SELECT * FROM listings WHERE id=?", (listing_id,)).fetchone()
    if not row:
        raise HTTPException(404, "no such listing")
    layers = body.layers if body.layers is not None else json.loads(row["layers"])
    cfg = registry.build_listing_config(listing_id, row["county_fips"], json.loads(row["parcel_ids"]), layers, body.thresholds, body.growing, row["title"])
    Path(row["config_path"]).write_text(yaml.safe_dump(cfg, sort_keys=False))
    with db() as con:
        con.execute("UPDATE listings SET layers=? WHERE id=?", (json.dumps(layers), listing_id))
    return {"listing_id": listing_id, "job_id": _enqueue(listing_id, body.pdf), "url": f"/listing/{listing_id}"}


@app.get("/api/listings")
def api_listings():
    with db() as con:
        rows = con.execute("SELECT * FROM listings ORDER BY created_at DESC").fetchall()
    return [_listing_row(r) for r in rows]


@app.get("/api/listings/{listing_id}")
def api_listing(listing_id: str):
    with db() as con:
        row = con.execute("SELECT * FROM listings WHERE id=?", (listing_id,)).fetchone()
    if not row:
        raise HTTPException(404, "no such listing")
    return _listing_row(row, with_geo=True)


@app.get("/api/jobs/{job_id}")
def api_job(job_id: str):
    with db() as con:
        row = con.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(404, "no such job")
    log = list(_logs.get(job_id, [])) or (row["log"] or "").splitlines()
    return {"status": row["status"], "step": row["step"], "steps_done": row["steps_done"], "steps_total": row["steps_total"],
            "log": log[-30:], "error": row["error"], "listing_id": row["listing_id"]}


@app.get("/api/listings/{listing_id}/report", response_class=HTMLResponse)
def api_report(listing_id: str):
    p = ROOT / "outputs" / "web" / listing_id / "report.html"
    if not p.exists():
        raise HTTPException(404, "report not generated yet")
    return HTMLResponse(p.read_text())


@app.get("/api/listings/{listing_id}/atlas.pdf")
def api_atlas(listing_id: str):
    out = ROOT / "outputs" / "web" / listing_id
    p = out / "atlas.pdf"
    if not p.exists():
        with db() as con:
            row = con.execute("SELECT * FROM listings WHERE id=?", (listing_id,)).fetchone()
        if not row or not (out / "evaluation.json").exists():
            raise HTTPException(404, "evaluation not available yet")
        with pipeline._lock:
            pipeline.run_step(pipeline.PDF_STEP, Path(row["config_path"]), lambda s: None)
    return FileResponse(p, media_type="application/pdf", filename=f"{listing_id}_atlas.pdf")


@app.get("/api/listings/{listing_id}/files/{name}")
def api_file(listing_id: str, name: str):
    if "/" in name or name.startswith("."):
        raise HTTPException(400, "bad name")
    p = ROOT / "outputs" / "web" / listing_id / name
    if not p.exists():
        raise HTTPException(404, "no such file")
    return FileResponse(p)


# ----------------------------------------------------------------------------- static
@app.get("/", response_class=HTMLResponse)
@app.get("/listing/{listing_id}", response_class=HTMLResponse)
def index(listing_id: str | None = None):
    return HTMLResponse((STATIC / "index.html").read_text())


@app.get("/app.js")
def app_js():
    return FileResponse(STATIC / "app.js", media_type="application/javascript")


@app.get("/app.css")
def app_css():
    return FileResponse(STATIC / "app.css", media_type="text/css")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
