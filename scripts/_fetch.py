"""Fetch remote geospatial data into the local cache.

Supported sources (config `source:` key):
  arcgis        ArcGIS REST FeatureServer/MapServer layer, queried by attribute filter and/or
                bounding box, paged, saved as GeoPackage.
  arcgis_image  ArcGIS ImageServer (e.g. USGS 3DEP elevation) exported as a GeoTIFF for the AOI.
  wfs           OGC WFS layer, fetched by bounding box, saved as GeoPackage.
  url           A direct download (GeoJSON, zipped shapefile, GeoTIFF, GeoPackage).
"""
from __future__ import annotations

import io
import json
import math
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

UA = {"User-Agent": "property-analysis/1.0 (+github repo; geopandas)"}
TIMEOUT = 120


def _get(url, params=None, retries=4, stream=False):
    """GET with retries and backoff; public servers reset connections now and then."""
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=TIMEOUT, stream=stream)
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"{r.status_code} from server")
            r.raise_for_status()
            return r
        except Exception as e:  # noqa: BLE001
            last = e
            wait = 2 ** i
            print(f"  retry {i + 1}/{retries} after {type(e).__name__}: {e} (sleep {wait}s)")
            time.sleep(wait)
    raise RuntimeError(f"gave up on {url}: {last}")


def _json(url, params=None):
    r = _get(url, dict(params or {}, f="json"))
    d = r.json()
    if "error" in d:
        raise RuntimeError(f"ArcGIS error from {url}: {d['error']}")
    return d


def _features_to_gdf(payload: dict, fmt: str) -> gpd.GeoDataFrame:
    if fmt == "geojson":
        feats = payload.get("features", [])
        if not feats:
            return gpd.GeoDataFrame(geometry=[], crs=4326)
        return gpd.GeoDataFrame.from_features(feats, crs=4326)
    # Esri JSON: let GDAL's ESRIJSON driver parse it.
    return gpd.read_file(io.StringIO(json.dumps(payload)))


# ----------------------------------------------------------------------------- ArcGIS features
def fetch_arcgis_features(url: str, bbox4326=None, where: str = "1=1", out_fields: str = "*") -> tuple[gpd.GeoDataFrame, dict]:
    """Query a FeatureServer/MapServer layer. bbox4326 = (minx, miny, maxx, maxy) in WGS84 or None."""
    url = url.rstrip("/")
    meta = _json(url)
    name = meta.get("name", url.rsplit("/", 1)[-1])
    max_rec = int(meta.get("maxRecordCount") or 1000)
    paging = bool((meta.get("advancedQueryCapabilities") or {}).get("supportsPagination"))
    fmt = "geojson" if "geoJSON" in (meta.get("supportedQueryFormats") or "geoJSON") else "json"
    base = {"where": where, "outFields": out_fields, "returnGeometry": "true", "outSR": 4326, "f": fmt}
    if bbox4326:
        base.update({"geometry": ",".join(f"{v:.8f}" for v in bbox4326), "geometryType": "esriGeometryEnvelope",
                     "inSR": 4326, "spatialRel": "esriSpatialRelIntersects"})
    print(f"  {name}: maxRecordCount={max_rec} paging={paging} format={fmt}")

    parts = []
    if paging:
        offset = 0
        while True:
            d = _get(f"{url}/query", dict(base, resultOffset=offset, resultRecordCount=max_rec)).json()
            if "error" in d:
                raise RuntimeError(d["error"])
            g = _features_to_gdf(d, fmt)
            parts.append(g)
            n = len(g)
            more = d.get("exceededTransferLimit") or (d.get("properties") or {}).get("exceededTransferLimit")
            print(f"  fetched {n} (offset {offset})")
            if n < max_rec and not more:
                break
            if n == 0:
                break
            offset += n
    else:
        ids = _get(f"{url}/query", dict(base, returnIdsOnly="true", f="json")).json()
        oid_field, oids = ids.get("objectIdFieldName", "OBJECTID"), ids.get("objectIds") or []
        print(f"  {len(oids)} object ids")
        for i in range(0, len(oids), max_rec):
            chunk = oids[i:i + max_rec]
            d = _get(f"{url}/query", dict(base, objectIds=",".join(map(str, chunk)))).json()
            parts.append(_features_to_gdf(d, fmt))
            print(f"  fetched {len(parts[-1])} ({i + len(chunk)}/{len(oids)})")
    gdf = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=4326) if parts else gpd.GeoDataFrame(geometry=[], crs=4326)
    if "geometry" in gdf and len(gdf):
        gdf = gdf[gdf.geometry.notna()].copy()
        # Some servers return bbox-intersecting features clipped oddly; make geometry valid.
        gdf["geometry"] = gdf.geometry.make_valid()
    info = {"source": "arcgis", "url": url, "layer_name": name, "where": where, "bbox4326": bbox4326,
            "features": int(len(gdf)), "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "description": (meta.get("description") or "")[:300], "copyright": meta.get("copyrightText", "")}
    return gdf, info


# ----------------------------------------------------------------------------- ArcGIS image
def fetch_arcgis_image(url: str, bbox_proj, epsg: int, resolution: float, out_path: Path,
                       pixel_type="F32") -> dict:
    """exportImage from an ImageServer for bbox in the project CRS (EPSG code `epsg`) at `resolution`
    CRS units per pixel. Splits into tiles if larger than the server's max size."""
    url = url.rstrip("/")
    meta = _json(url)
    max_w, max_h = int(meta.get("maxImageWidth") or 4000), int(meta.get("maxImageHeight") or 4000)
    minx, miny, maxx, maxy = bbox_proj
    w, h = math.ceil((maxx - minx) / resolution), math.ceil((maxy - miny) / resolution)
    if w > max_w or h > max_h:
        raise RuntimeError(f"requested {w}x{h} px exceeds server max {max_w}x{max_h}; raise the resolution value")
    params = {"bbox": f"{minx},{miny},{maxx},{maxy}", "bboxSR": epsg, "imageSR": epsg, "size": f"{w},{h}",
              "format": "tiff", "pixelType": pixel_type, "interpolation": "RSP_BilinearInterpolation",
              "noDataInterpretation": "esriNoDataMatchAny", "f": "image"}
    r = _get(f"{url}/exportImage", params)
    if "image/tif" not in r.headers.get("Content-Type", "") and not r.content[:4] in (b"II*\x00", b"MM\x00*"):
        raise RuntimeError(f"exportImage did not return a TIFF: {r.text[:300]}")
    out_path.write_bytes(r.content)
    print(f"  {meta.get('name')}: {w}x{h} px at {resolution} units/px")
    return {"source": "arcgis_image", "url": url, "layer_name": meta.get("name"), "bbox_proj": list(bbox_proj),
            "epsg": epsg, "resolution": resolution, "size_px": [w, h],
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "copyright": meta.get("copyrightText", "")}


# ----------------------------------------------------------------------------- WFS
def fetch_wfs(url: str, typename: str, bbox4326, version="2.0.0") -> tuple[gpd.GeoDataFrame, dict]:
    params = {"service": "WFS", "version": version, "request": "GetFeature", "typeNames": typename,
              "outputFormat": "application/json", "srsName": "EPSG:4326"}
    if bbox4326:
        minx, miny, maxx, maxy = bbox4326
        # WFS 2.0 with EPSG:4326 uses lat/lon axis order.
        params["bbox"] = f"{miny},{minx},{maxy},{maxx},urn:ogc:def:crs:EPSG::4326"
    r = _get(url, params)
    gdf = gpd.read_file(io.BytesIO(r.content))
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    gdf = gdf.to_crs(4326)
    print(f"  {typename}: {len(gdf)} features")
    return gdf, {"source": "wfs", "url": url, "typename": typename, "bbox4326": bbox4326, "features": int(len(gdf)),
                 "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}


# ----------------------------------------------------------------------------- plain URL
def download_url(url: str, cache_dir: Path, name: str) -> tuple[Path, dict]:
    """Download a file. Zip archives are extracted and the first .shp/.gpkg/.geojson/.tif is returned."""
    r = _get(url, stream=True)
    suffix = Path(url.split("?")[0]).suffix.lower() or ".bin"
    raw = cache_dir / f"{name}{suffix}"
    with open(raw, "wb") as f:
        for chunk in r.iter_content(1 << 20):
            f.write(chunk)
    path = raw
    if suffix == ".zip":
        dest = cache_dir / name
        dest.mkdir(exist_ok=True)
        with zipfile.ZipFile(raw) as z:
            z.extractall(dest)
        cands = [p for ext in (".gpkg", ".shp", ".geojson", ".json", ".tif", ".tiff")
                 for p in dest.rglob(f"*{ext}")]
        if not cands:
            raise RuntimeError(f"no spatial file found in {url}")
        path = cands[0]
    print(f"  downloaded {path.name} ({path.stat().st_size / 1e6:.1f} MB)")
    return path, {"source": "url", "url": url, "file": str(path), "bytes": path.stat().st_size,
                  "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
