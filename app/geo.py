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


def _service_fields(pc: dict) -> list[str]:
    """Fields to request from the parcel service: the real id/label columns (composite or single)."""
    fields = list(pc.get("id_fields") or [pc["id_field"]]) + list(pc.get("label_fields") or ([pc["label_field"]] if pc.get("label_field") else []))
    if pc.get("acres_field"):
        fields.append(pc["acres_field"])
    return list(dict.fromkeys(f for f in fields if f))


def _ident(pc: dict, props: dict) -> tuple[str, str]:
    """(parcel id, label) from a feature's properties, honouring composite ids and multi-field labels."""
    if pc.get("id_fields"):
        pid = "-".join(str(props.get(f, "")).strip() for f in pc["id_fields"])
    else:
        pid = str(props.get(pc["id_field"]))
    if pc.get("label_fields"):
        label = " ".join(str(props.get(f)).strip() for f in pc["label_fields"] if props.get(f) not in (None, "", "None"))
    else:
        label = str(props.get(pc.get("label_field")) or pid)
    return pid, label or pid


def parcel_at(lat: float, lon: float, fips: str | None = None, radius_m: float = 40.0) -> dict | None:
    fips = fips or county_for_point(lat, lon)
    c = county(fips) if fips else None
    if not c:
        return None
    pc = c["parcels"]
    src = catalog()["overlays"][pc["use"]]
    fields = _service_fields(pc)

    def query(geometry, gtype):
        for attempt in range(3):
            try:
                r = httpx.get(src["url"].rstrip("/") + "/query",
                              params={"geometry": geometry, "geometryType": gtype, "inSR": 4326,
                                      "spatialRel": "esriSpatialRelIntersects", "outFields": ",".join(fields),
                                      "where": pc.get("filter_where") or "1=1",
                                      "returnGeometry": "true", "outSR": 4326, "f": "geojson"}, headers=UA, timeout=30)
                r.raise_for_status()
                return r.json().get("features") or []
            except Exception:  # noqa: BLE001
                if attempt == 2:
                    raise
                time.sleep(1 + attempt)

    feats = query(f"{lon},{lat}", "esriGeometryPoint")
    if not feats and radius_m:
        # Geocoded addresses often land on the street, outside every parcel: take the nearest
        # parcel within radius_m instead.
        d = radius_m / 111_000.0
        feats = query(f"{lon - d},{lat - d},{lon + d},{lat - d + 2 * d}", "esriGeometryEnvelope")
        if feats:
            from shapely.geometry import Point, shape
            pt = Point(lon, lat)
            feats.sort(key=lambda ft: shape(ft["geometry"]).distance(pt) if ft.get("geometry") else 9e9)
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
    pid, label = _ident(pc, props)
    return {"county_fips": fips, "parcel_id": pid, "label": label,
            "acres": round(float(acres), 3) if acres is not None else None, "geometry": f.get("geometry")}


def parcel_by_address(fips: str, address: str) -> dict | None:
    """Find a parcel by its situs address in the county parcel service (house number + street
    prefix match). More reliable than a geocoded point, which the Census geocoder interpolates
    along the street and can place several lots away."""
    import re
    c = county(fips)
    if not c or not (c["parcels"].get("label_field") or c["parcels"].get("address_where")):
        return None
    pc = c["parcels"]
    src = catalog()["overlays"][pc["use"]]
    first = address.split(",")[0].strip().upper()
    m = re.match(r"^(\d+[A-Z]?)\s+(.+?)\s*$", first)
    if not m:
        return None
    house, street = m.group(1), m.group(2)
    # drop the suffix word (RD, AVE, ...) so 'BARREN HILL RD' matches 'BARREN HILL ROAD' too
    words = street.split()
    core = " ".join(words[:-1]) if len(words) > 1 else street
    like = f"{house} {core}%".replace("'", "''")
    fields = _service_fields(pc)
    if pc.get("address_where"):   # e.g. Philadelphia DOR: house = {house} AND UPPER(stnam) LIKE '{street}%'
        where = pc["address_where"].format(house=re.sub(r"\D", "", house) or "0", street=core.replace("'", "''"))
    else:
        where = f"UPPER({pc['label_field']}) LIKE '{like}'"
        if pc.get("filter_where"):
            where += f" AND ({pc['filter_where']})"
    r = httpx.get(src["url"].rstrip("/") + "/query",
                  params={"where": where, "outFields": ",".join(fields),
                          "returnGeometry": "true", "outSR": 4326, "f": "geojson"}, headers=UA, timeout=30)
    r.raise_for_status()
    feats = r.json().get("features") or []
    if not feats:
        return None
    f = feats[0]
    props = f.get("properties") or {}
    acres = props.get(pc.get("acres_field")) if pc.get("acres_field") else None
    if acres is None and f.get("geometry"):
        import geopandas as gpd
        from shapely.geometry import shape
        g = gpd.GeoSeries([shape(f["geometry"])], crs=4326).to_crs(c.get("crs", "EPSG:2272"))
        acres = round(float(g.area.iloc[0]) / 43560, 3)
    pid, label = _ident(pc, props)
    return {"county_fips": fips, "parcel_id": pid, "label": label,
            "acres": round(float(acres), 3) if acres is not None else None, "geometry": f.get("geometry"), "matched_by": "address"}
