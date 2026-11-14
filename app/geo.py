"""Geocoding and parcel lookup against public services."""
from __future__ import annotations

import json
import time

import httpx

from .registry import catalog, county

UA = {"User-Agent": "parcel-analysis-web/0.1"}
CENSUS = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"
_meta_cache: dict[str, dict] = {}


def geocode(q: str) -> dict | None:
    r = httpx.get(CENSUS, params={"address": q, "benchmark": "Public_AR_Current", "vintage": "Current_Current", "format": "json"},
                  headers=UA, timeout=30)
    r.raise_for_status()
    m = (r.json().get("result") or {}).get("addressMatches") or []
    if not m:
        return None
    best = m[0]
    cty = ((best.get("geographies") or {}).get("Counties") or [{}])[0]
    fips = cty.get("GEOID")
    return {"lat": best["coordinates"]["y"], "lon": best["coordinates"]["x"], "matched": best.get("matchedAddress"),
            "county_fips": fips, "county_name": cty.get("NAME"), "state": (best.get("addressComponents") or {}).get("state"),
            "supported": county(fips) is not None}


def county_for_point(lat: float, lon: float) -> str | None:
    r = httpx.get("https://geocoding.geo.census.gov/geocoder/geographies/coordinates",
                  params={"x": lon, "y": lat, "benchmark": "Public_AR_Current", "vintage": "Current_Current", "format": "json"},
                  headers=UA, timeout=30)
    r.raise_for_status()
    cty = ((r.json().get("result") or {}).get("geographies") or {}).get("Counties") or []
    return cty[0].get("GEOID") if cty else None


def _layer_meta(url: str) -> dict:
    if url not in _meta_cache:
        r = httpx.get(url, params={"f": "json"}, headers=UA, timeout=30)
        r.raise_for_status()
        _meta_cache[url] = r.json()
    return _meta_cache[url]


def parcel_at(lat: float, lon: float, fips: str | None = None) -> dict | None:
    fips = fips or county_for_point(lat, lon)
    c = county(fips) if fips else None
    if not c:
        return None
    pc = c["parcels"]
    src = catalog()["overlays"][pc["use"]]
    fields = [pc["id_field"], pc.get("label_field")] + ([pc["acres_field"]] if pc.get("acres_field") else [])
    fields = [f for f in fields if f]
    for attempt in range(3):
        try:
            r = httpx.get(src["url"].rstrip("/") + "/query",
                          params={"geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint", "inSR": 4326,
                                  "spatialRel": "esriSpatialRelIntersects", "outFields": ",".join(fields),
                                  "returnGeometry": "true", "outSR": 4326, "f": "geojson"}, headers=UA, timeout=30)
            r.raise_for_status()
            d = r.json()
            break
        except Exception:  # noqa: BLE001
            if attempt == 2:
                raise
            time.sleep(1 + attempt)
    feats = d.get("features") or []
    if not feats:
        return None
    f = feats[0]
    props = f.get("properties") or {}
    acres = props.get(pc.get("acres_field")) if pc.get("acres_field") else None
    if acres is None and f.get("geometry"):
        # compute from geometry in the county CRS
        import geopandas as gpd
        from shapely.geometry import shape
        g = gpd.GeoSeries([shape(f["geometry"])], crs=4326).to_crs(c.get("crs", "EPSG:2272"))
        acres = round(float(g.area.iloc[0]) / 43560, 3)
    return {"county_fips": fips, "parcel_id": str(props.get(pc["id_field"])),
            "label": str(props.get(pc.get("label_field")) or props.get(pc["id_field"])),
            "acres": round(float(acres), 3) if acres is not None else None, "geometry": f.get("geometry")}
