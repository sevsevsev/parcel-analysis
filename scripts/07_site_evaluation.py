"""Site evaluation for land shopping.

Answers, for the whole property and per parcel:
  1. Buildable area  - ground that is gentle enough, outside setbacks, flood zones, stream and
                       wetland buffers; the largest contiguous building pads and their dimensions.
  2. Sun exposure    - aspect, and hours of direct sun on Dec 21 / Mar 21 / Jun 21 computed by
                       casting shadows across the bare-earth DEM (tree canopy is NOT modelled).
  3. Stormwater      - D8 flow routing on the DEM: run-on from upslope neighbours, concentrated
                       flow paths, discharge points, ponding areas; soil infiltration from SSURGO.
  4. Services        - zoning, sewer and water service areas, road frontage, existing buildings.
Writes outputs/<listing>/evaluation.md, evaluation.json, evaluation.gpkg, rasters and maps.
"""
import heapq
import json
import math
import sys
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize, shapes
from shapely.geometry import LineString, Point, shape
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).parent))
from _common import (area_acres, cache_path, crs_unit_to_feet, find_spec, layer_path, length_feet,  # noqa: E402
                     load_config, property_path, read_role, write_md)
from _maps import add_basemap, add_contours, decorate, label_parcels, new_map, plt  # noqa: E402
from pyproj import CRS  # noqa: E402

warnings.filterwarnings("ignore")
ASPECT_CLASSES = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


# ------------------------------------------------------------------ grid helpers
class Grid:
    def __init__(self, cfg):
        dem_spec = find_spec(cfg, "dem", "rasters")
        if not dem_spec:
            sys.exit("site evaluation needs a DEM (rasters entry with role: dem)")
        self.z_units = dem_spec.get("z_units", "m")
        with rasterio.open(layer_path(dict(dem_spec, kind="raster"), cfg)) as src:
            self.transform, self.crs, self.profile = src.transform, src.crs, src.profile
            z = src.read(1).astype("float64")
            if src.nodata is not None:
                z[z == src.nodata] = np.nan
            z[z < -1000] = np.nan
        self.k_ft = crs_unit_to_feet(CRS(cfg["crs"]))                 # crs unit -> ft
        z_to_crs = (3.280839895 / self.k_ft) if self.z_units == "m" else (1.0 / self.k_ft)
        self.z = z * z_to_crs                                           # elevation in CRS units
        self.z_ft = self.z * self.k_ft
        self.res = self.transform.a
        self.cell_acres = self.res * self.res * self.k_ft ** 2 / 43560.0
        self.shape = z.shape
        with rasterio.open(cfg["_out"] / "slope_pct.tif") as s:
            self.slope = s.read(1).astype("float64")
            self.slope[self.slope < 0] = np.nan
        with rasterio.open(cfg["_out"] / "aspect_deg.tif") as s:
            self.aspect = s.read(1).astype("float64")
            self.aspect[self.aspect < 0] = np.nan

    def mask(self, geoms):
        geoms = [g for g in geoms if g is not None and not g.is_empty]
        if not geoms:
            return np.zeros(self.shape, dtype=bool)
        return rasterize(((g, 1) for g in geoms), out_shape=self.shape, transform=self.transform,
                         fill=0, dtype="uint8").astype(bool)

    def ids(self, gdf):
        return rasterize(((g, i + 1) for i, g in enumerate(gdf.geometry)), out_shape=self.shape,
                         transform=self.transform, fill=0, dtype="int32")

    def polygons(self, mask, crs):
        feats = [shape(g) for g, v in shapes(mask.astype("uint8"), mask=mask, transform=self.transform) if v == 1]
        return gpd.GeoDataFrame(geometry=feats, crs=crs)

    def write(self, path, arr, nodata=-9999):
        prof = dict(self.profile, dtype="float32", count=1, nodata=nodata, compress="lzw")
        with rasterio.open(path, "w", **prof) as dst:
            dst.write(np.where(np.isnan(arr), nodata, arr).astype("float32"), 1)

    def xy(self, row, col):
        return self.transform.c + (col + 0.5) * self.transform.a, self.transform.f + (row + 0.5) * self.transform.e


# ------------------------------------------------------------------ 1. buildable
def buildable_analysis(cfg, G, parcels, boundary, layers, ev, acc_acres=None):
    idf = cfg["parcels"]["id_field"]
    prop = G.mask(boundary.geometry)
    k = G.k_ft
    setback = ev.get("property_line_setback_ft", 50) / k
    inner = boundary.geometry.buffer(-setback)
    masks = {"steep": prop & (G.slope > ev.get("max_build_slope_pct", 15)),
             "setback": prop & ~G.mask(inner)}
    flood = layers.get("floodplain")
    if flood is not None and len(flood):
        zf = flood[flood["FLD_ZONE"].isin(ev.get("exclude_flood_zones", []))] if "FLD_ZONE" in flood else flood.iloc[0:0]
        masks["flood"] = prop & G.mask(zf.geometry)
    water = []
    for role in ("streams", "waterbodies"):
        g = layers.get(role)
        if g is not None and len(g):
            water += list(g.geometry.buffer(ev.get("stream_buffer_ft", 100) / k))
    if water:
        masks["stream_buffer"] = prop & G.mask(water)
    wet = layers.get("wetlands")
    if wet is not None and len(wet):
        masks["wetland_buffer"] = prop & G.mask(wet.geometry.buffer(ev.get("wetland_buffer_ft", 50) / k))
    if acc_acres is not None and ev.get("drainage_way_threshold_acres"):
        # Unmapped channels: ground draining at least N acres gets a buffer like a stream.
        chan = acc_acres >= float(ev["drainage_way_threshold_acres"])
        if chan.any():
            cp = G.polygons(chan, parcels.crs)
            masks["drainage_way_buffer"] = prop & G.mask(cp.geometry.buffer(ev.get("drainage_way_buffer_ft", 50) / k))
    constrained = np.zeros(G.shape, dtype=bool)
    for m in masks.values():
        constrained |= m
    build = prop & ~constrained & ~np.isnan(G.slope)
    other = np.zeros(G.shape, dtype=bool)          # every constraint except slope
    for k_, m in masks.items():
        if k_ != "steep":
            other |= m
    relaxed = prop & ~np.isnan(G.slope) & ~other & (G.slope <= 25)

    pid = G.ids(parcels)
    rows = []
    for i, r in parcels.iterrows():
        m = pid == i + 1
        rows.append({idf: r[idf], "parcel_acres": round(m.sum() * G.cell_acres, 3),
                     "buildable_acres": round((build & m).sum() * G.cell_acres, 3),
                     "buildable_pct": round(100 * (build & m).sum() / max(m.sum(), 1), 1),
                     "steep_acres": round((masks["steep"] & m).sum() * G.cell_acres, 3)})
    by_parcel = pd.DataFrame(rows)

    pads = G.polygons(build, parcels.crs)
    pads["acres"] = area_acres(pads.geometry)
    pads = pads[pads["acres"] >= ev.get("min_building_pad_acres", 0.5)].sort_values("acres", ascending=False)
    pad_rows = []
    for j, (_, p) in enumerate(pads.iterrows(), 1):
        rect = p.geometry.minimum_rotated_rectangle
        xs, ys = rect.exterior.coords.xy
        e1 = math.hypot(xs[1] - xs[0], ys[1] - ys[0]) * k
        e2 = math.hypot(xs[2] - xs[1], ys[2] - ys[1]) * k
        m = G.mask([p.geometry])
        c = p.geometry.representative_point()
        pad_rows.append({"pad": j, "acres": round(p.acres, 3), "approx_dims_ft": f"{max(e1, e2):.0f} x {min(e1, e2):.0f}",
                         "mean_slope_pct": round(float(np.nanmean(G.slope[m])), 1),
                         "parcel": parcels.iloc[int(pid[m].max()) - 1][idf] if pid[m].max() > 0 else "",
                         "geometry": p.geometry})
    pads = gpd.GeoDataFrame(pad_rows, geometry="geometry", crs=parcels.crs) if pad_rows else pads.iloc[0:0]

    summary = {"property_acres": round(prop.sum() * G.cell_acres, 3),
               "buildable_acres": round(build.sum() * G.cell_acres, 3),
               "buildable_pct": round(100 * build.sum() / prop.sum(), 1),
               "buildable_if_slope_25_acres": round(relaxed.sum() * G.cell_acres, 3),
               "removed_by": {k_: round(m.sum() * G.cell_acres, 3) for k_, m in masks.items()},
               "pads": [{k_: v for k_, v in r.items() if k_ != "geometry"} for r in pad_rows]}
    return build, masks, by_parcel, pads, summary


# ------------------------------------------------------------------ 2. sun
def sun_position(lat_deg, doy, hour):
    """Solar altitude and azimuth (degrees, azimuth clockwise from north) for local solar time."""
    lat = math.radians(lat_deg)
    decl = math.radians(23.44) * math.sin(2 * math.pi * (284 + doy) / 365)
    ha = math.radians(15 * (hour - 12))
    alt = math.asin(math.sin(lat) * math.sin(decl) + math.cos(lat) * math.cos(decl) * math.cos(ha))
    az = math.atan2(-math.sin(ha), math.cos(lat) * math.tan(decl) - math.sin(lat) * math.cos(ha))
    return math.degrees(alt), (math.degrees(az) + 360) % 360


def shadowed(G, alt_deg, az_deg, max_dist_cells=300):
    """True where a cell is in terrain shadow for the given sun position (ray march on the DEM)."""
    z = np.where(np.isnan(G.z), -1e9, G.z)
    tan_alt = math.tan(math.radians(alt_deg))
    # direction towards the sun in array coordinates (row increases southward)
    dx, dy = math.sin(math.radians(az_deg)), -math.cos(math.radians(az_deg))
    hmax = np.full(G.shape, -np.inf)
    H, W = G.shape
    relief = float(np.nanmax(G.z) - np.nanmin(G.z))
    for d in range(1, max_dist_cells + 1):
        if d * G.res * tan_alt > relief:      # ray is above every point in the AOI from here on
            break
        oc, orow = int(round(dx * d)), int(round(dy * d))
        shifted = np.full(G.shape, -1e9)
        rs, re_ = max(0, -orow), min(H, H - orow)
        cs, ce = max(0, -oc), min(W, W - oc)
        if rs >= re_ or cs >= ce:
            break
        shifted[rs:re_, cs:ce] = z[rs + orow:re_ + orow, cs + oc:ce + oc]
        rise = shifted - z - d * G.res * tan_alt
        hmax = np.maximum(hmax, rise)
    shadow = hmax > 0
    return shadow


def _sun_cache_dir(cfg, G):
    """Shared cache folder for sun rasters, keyed by the DEM's location key (terrain only)."""
    dem_spec = find_spec(cfg, "dem", "rasters")
    meta = cache_path(cfg, dict(dem_spec, kind="raster")).with_suffix(".json") if dem_spec else None
    if not meta or not meta.exists():
        return None
    key = json.loads(meta.read_text()).get("cache_key")
    if not key:
        return None
    d = cfg["_root"] / "data" / "cache" / "_shared" / "derived" / f"sun_{key}_{G.shape[0]}x{G.shape[1]}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def sun_analysis(cfg, G, parcels, boundary, build, lat):
    prop = G.mask(boundary.geometry)
    idf = cfg["parcels"]["id_field"]
    slope_rad = np.arctan(np.nan_to_num(G.slope) / 100)
    aspect_rad = np.radians(np.nan_to_num(G.aspect))
    dates = {"dec21": 355, "mar21": 80, "jun21": 172}
    hours, index = {}, {}
    cache_d = _sun_cache_dir(cfg, G)
    for name, doy in dates.items():
        if cache_d and (cache_d / f"hours_{name}.npy").exists() and (cache_d / f"index_{name}.npy").exists():
            hours[name] = np.load(cache_d / f"hours_{name}.npy")
            index[name] = np.load(cache_d / f"index_{name}.npy")
            if hours[name].shape == G.shape:
                G.write(cfg["_out"] / f"sun_hours_{name}.tif", np.where(np.isnan(G.z), np.nan, hours[name]))
                G.write(cfg["_out"] / f"solar_index_{name}.tif", np.where(np.isnan(G.z), np.nan, index[name]))
                print(f"  sun {name}: from shared cache")
                continue
        direct = np.zeros(G.shape)
        irr, irr_flat = np.zeros(G.shape), 0.0
        for h100 in range(500, 2000, 25):                 # 05:00-19:45 in 15-minute steps
            hour = h100 / 100
            alt, az = sun_position(lat, doy, hour)
            if alt <= 2:
                continue
            sh = shadowed(G, alt, az)
            zen = math.radians(90 - alt)
            cosi = (np.cos(slope_rad) * math.cos(zen) +
                    np.sin(slope_rad) * math.sin(zen) * np.cos(math.radians(az) - aspect_rad))
            lit = (~sh) & (cosi > 0)
            direct += lit * 0.25
            irr += np.where(lit, cosi, 0.0)               # direct-beam irradiance on the slope, relative units
            irr_flat += math.cos(zen)                     # the same for a flat, unshaded cell
        hours[name] = direct
        index[name] = irr / irr_flat                      # 1.0 = flat unshaded; >1 faces the low sun; <1 turns away
        if cache_d:
            np.save(cache_d / f"hours_{name}.npy", direct)
            np.save(cache_d / f"index_{name}.npy", index[name])
        G.write(cfg["_out"] / f"sun_hours_{name}.tif", np.where(np.isnan(G.z), np.nan, direct))
        G.write(cfg["_out"] / f"solar_index_{name}.tif", np.where(np.isnan(G.z), np.nan, index[name]))

    # aspect classes
    flat = (G.slope < 3)
    cls = np.full(G.shape, -1, dtype=int)
    cls[~flat] = ((G.aspect[~flat] + 22.5) // 45).astype(int) % 8
    rows = [{"aspect": "flat (<3%)", "acres": round((prop & flat).sum() * G.cell_acres, 3),
             "buildable_acres": round((build & flat).sum() * G.cell_acres, 3)}]
    for i, a in enumerate(ASPECT_CLASSES):
        m = cls == i
        rows.append({"aspect": a, "acres": round((prop & m).sum() * G.cell_acres, 3),
                     "buildable_acres": round((build & m).sum() * G.cell_acres, 3)})
    aspects = pd.DataFrame(rows)
    aspects["pct"] = (100 * aspects["acres"] / aspects["acres"].sum()).round(1)
    south = prop & (flat | np.isin(cls, [3, 4, 5]))
    pid = G.ids(parcels)
    per_parcel = []
    for i, r in parcels.iterrows():
        m = pid == i + 1
        per_parcel.append({idf: r[idf],
                           "dec21_sun_hours_mean": round(float(hours["dec21"][m].mean()), 1),
                           "dec21_solar_index": round(float(index["dec21"][m].mean()), 2),
                           "jun21_sun_hours_mean": round(float(hours["jun21"][m].mean()), 1),
                           "south_or_flat_pct": round(100 * (south & m).sum() / max(m.sum(), 1), 1)})
    summary = {"latitude": round(lat, 4),
               "dec21_sun_hours_property_mean": round(float(hours["dec21"][prop].mean()), 1),
               "dec21_sun_hours_buildable_mean": round(float(hours["dec21"][build].mean()), 1) if build.any() else None,
               "dec21_solar_index_property": round(float(index["dec21"][prop].mean()), 2),
               "dec21_solar_index_buildable": round(float(index["dec21"][build].mean()), 2) if build.any() else None,
               "jun21_solar_index_property": round(float(index["jun21"][prop].mean()), 2),
               "mar21_sun_hours_property_mean": round(float(hours["mar21"][prop].mean()), 1),
               "jun21_sun_hours_property_mean": round(float(hours["jun21"][prop].mean()), 1),
               "dec21_hours_at_flat_unshaded": round(sum(0.25 for h100 in range(500, 2000, 25)
                                                         if sun_position(lat, 355, h100 / 100)[0] > 2), 1),
               "south_or_flat_pct": round(100 * south.sum() / prop.sum(), 1),
               "buildable_with_4h_winter_sun_acres": round((build & (hours["dec21"] >= 4)).sum() * G.cell_acres, 3)}
    hours["index_dec21"] = index["dec21"]
    return hours, aspects, pd.DataFrame(per_parcel), summary


# ------------------------------------------------------------------ 3. stormwater
def fill_and_route(z):
    """Priority-flood depression filling, D8 flow direction and accumulation (cells)."""
    H, W = z.shape
    zf = np.where(np.isnan(z), -1e9, z).copy()
    filled = zf.copy()
    closed = np.zeros((H, W), dtype=bool)
    heap = []
    for r in range(H):
        for c in (0, W - 1):
            heap.append((zf[r, c], r, c)); closed[r, c] = True
    for c in range(1, W - 1):
        for r in (0, H - 1):
            heap.append((zf[r, c], r, c)); closed[r, c] = True
    heapq.heapify(heap)
    nbrs = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    eps = 1e-4
    while heap:
        zc, r, c = heapq.heappop(heap)
        for dr, dc in nbrs:
            rr, cc = r + dr, c + dc
            if 0 <= rr < H and 0 <= cc < W and not closed[rr, cc]:
                closed[rr, cc] = True
                if filled[rr, cc] <= zc:
                    filled[rr, cc] = zc + eps
                heapq.heappush(heap, (filled[rr, cc], rr, cc))
    # D8 direction: index into nbrs of steepest descent, -1 = outlet / edge
    dist = np.array([math.sqrt(2), 1, math.sqrt(2), 1, 1, math.sqrt(2), 1, math.sqrt(2)])
    best = np.full((H, W), -1, dtype=int)
    best_drop = np.zeros((H, W))
    pad = np.pad(filled, 1, constant_values=-1e12)
    for i, (dr, dc) in enumerate(nbrs):
        drop = (filled - pad[1 + dr:H + 1 + dr, 1 + dc:W + 1 + dc]) / dist[i]
        better = drop > best_drop
        best[better] = i
        best_drop[better] = drop[better]
    # accumulation: visit from high to low
    acc = np.ones((H, W))
    order = np.argsort(filled, axis=None)[::-1]
    rows, cols = np.unravel_index(order, (H, W))
    for r, c in zip(rows, cols):
        i = best[r, c]
        if i >= 0:
            rr, cc = r + nbrs[i][0], c + nbrs[i][1]
            if 0 <= rr < H and 0 <= cc < W:
                acc[rr, cc] += acc[r, c]
    down_r = np.where(best >= 0, np.arange(H)[:, None] + np.array([n[0] for n in nbrs])[np.clip(best, 0, 7)], -1)
    down_c = np.where(best >= 0, np.arange(W)[None, :] + np.array([n[1] for n in nbrs])[np.clip(best, 0, 7)], -1)
    return filled, best, acc, down_r, down_c


def stormwater_analysis(cfg, G, parcels, boundary, build, layers, routed=None):
    idf = cfg["parcels"]["id_field"]
    prop = G.mask(boundary.geometry)
    filled, fdir, acc, dr, dc = routed if routed is not None else fill_and_route(G.z)
    acc_acres = acc * G.cell_acres
    G.write(cfg["_out"] / "flow_accum_acres.tif", acc_acres)
    H, W = G.shape
    inside = prop
    valid = (dr >= 0) & (dr < H) & (dc >= 0) & (dc < W)
    down_inside = np.zeros(G.shape, dtype=bool)
    down_inside[valid] = inside[dr[valid], dc[valid]]
    # run-on: outside cells that drain directly into the property
    runon_cells = (~inside) & valid & down_inside
    runon_acres = float(acc_acres[runon_cells].sum())
    # outlets: inside cells draining out
    outlet_cells = inside & (~valid | ~down_inside)
    pts = []
    rr, cc = np.where(outlet_cells)
    order = np.argsort(acc_acres[rr, cc])[::-1]
    pid = G.ids(parcels)
    for k_ in order[:40]:
        r, c = rr[k_], cc[k_]
        if acc_acres[r, c] < 0.25:
            break
        x, y = G.xy(r, c)
        # keep well-separated outlets
        if any(math.hypot(x - p["x"], y - p["y"]) * G.k_ft < 100 for p in pts):
            continue
        pts.append({"x": x, "y": y, "contributing_acres": round(float(acc_acres[r, c]), 2),
                    "parcel": parcels.iloc[int(pid[r, c]) - 1][idf] if pid[r, c] > 0 else ""})
        if len(pts) >= 5:
            break
    outlets = gpd.GeoDataFrame(pts, geometry=[Point(p["x"], p["y"]) for p in pts], crs=parcels.crs) if pts \
        else gpd.GeoDataFrame(columns=["contributing_acres", "parcel", "geometry"], geometry="geometry", crs=parcels.crs)
    # concentrated flow paths inside the property
    thresh = float(cfg.get("evaluation", {}).get("flow_path_threshold_acres", 1.0))
    paths_mask = inside & (acc_acres >= thresh)
    paths = G.polygons(paths_mask, parcels.crs)
    flow_len_ft = float(paths_mask.sum()) * G.res * G.k_ft          # approx. one cell length per cell
    # ponding (depressions filled > 0.5 ft)
    pond = inside & ((filled - np.where(np.isnan(G.z), -1e9, G.z)) * G.k_ft > 0.5)
    ponds = G.polygons(pond, parcels.crs)
    pond_acres = float(pond.sum() * G.cell_acres)
    # drains onto buildable pads: run-on reaching buildable cells
    # soils
    soils = layers.get("soils")
    soil_rows, soil_summary = [], {}
    if soils is not None and len(soils):
        s = gpd.overlay(boundary[["geometry"]], soils, how="intersection", keep_geom_type=True)
        s["acres"] = area_acres(s.geometry)
        grp = s.groupby(["musym", "muname", "hydgrp", "drainagecl", "hydricrating"], dropna=False)["acres"].sum().reset_index()
        grp["pct"] = (100 * grp["acres"] / grp["acres"].sum()).round(1)
        grp["acres"] = grp["acres"].round(3)
        soil_rows = grp.sort_values("acres", ascending=False)
        hg = s.groupby("hydgrp", dropna=False)["acres"].sum()
        tot = hg.sum()
        gentle = prop & (G.slope <= 15)
        ab = G.mask(s[s["hydgrp"].isin(["A", "B"])].geometry) if "hydgrp" in s else np.zeros(G.shape, dtype=bool)
        soil_summary = {"hydrologic_group_pct": {str(k_): round(float(100 * v / tot), 1) for k_, v in hg.items()},
                        "good_infiltration_pct(A/B)": round(float(100 * hg[hg.index.isin(["A", "B"])].sum() / tot), 1),
                        "good_infiltration_on_gentle_ground_pct": round(100 * float((ab & gentle).sum()) / max(int(gentle.sum()), 1), 1),
                        "gentle_ground_acres": round(float(gentle.sum() * G.cell_acres), 3),
                        "hydric_acres": round(float(s.loc[s["hydricrating"] == "Yes", "acres"].sum()), 3),
                        "poorly_drained_acres": round(float(s.loc[s["drainagecl"].fillna("").str.contains("oorly"), "acres"].sum()), 3),
                        "min_depth_to_restrictive_cm": None if "resdept_cm" not in s else
                        (None if s["resdept_cm"].isna().all() else int(s["resdept_cm"].min()))}
    summary = {"runon_from_offsite_acres": round(runon_acres, 2),
               "outlets": [{k_: v for k_, v in p.items() if k_ not in ("x", "y")} for p in pts],
               "concentrated_flow_path_ft": round(flow_len_ft, 0), "flow_path_threshold_acres": thresh,
               "ponding_acres": round(pond_acres, 3), "soils": soil_summary}
    return acc_acres, outlets, paths, ponds, soil_rows, summary


# ------------------------------------------------------------------ 4. services
def services_analysis(cfg, parcels, boundary, layers):
    idf = cfg["parcels"]["id_field"]
    out = {}
    total = float(area_acres(boundary.geometry).iloc[0])

    def coverage(role, field):
        """Percent of the property inside each named service area, or None if the layer is absent."""
        g = layers.get(role)
        if g is None:
            return None
        if len(g) == 0:
            return {}
        x = gpd.overlay(boundary[["geometry"]], g, how="intersection", keep_geom_type=True)
        x["acres"] = area_acres(x.geometry)
        t = x.groupby(field)["acres"].sum()
        return {str(k_): round(float(100 * v / total), 1) for k_, v in t.items()}

    z = layers.get("zoning")
    if z is not None and len(z):
        x = gpd.overlay(boundary[["geometry"]], z, how="intersection", keep_geom_type=True)
        x["acres"] = area_acres(x.geometry)
        cols = [c for c in ("Code", "Name", "Type", "Municipali", "WebSite") if c in x.columns]
        if not cols:  # a layer with other field names: use its configured class field
            spec = find_spec(cfg, "zoning")
            cf = spec.get("class_field") if spec else None
            cols = [cf] if cf and cf in x.columns else [c for c in x.columns if c not in ("geometry", "acres")][:2]
        if cols:
            out["zoning"] = x.groupby(cols, dropna=False)["acres"].sum().round(3).reset_index().to_dict("records")
    out["sewer_pct"] = coverage("sewer", "Name")
    out["water_pct"] = coverage("water", "Name")
    roads = layers.get("roads")
    if roads is not None and len(roads):
        name_col = next((c for c in ("St_Name", "st_name", "NAME", "name", "FULLNAME") if c in roads.columns), None)
        type_col = next((c for c in ("St_PosTyp", "st_type", "St_Type") if c in roads.columns), None)
        edge = boundary.geometry.iloc[0].boundary
        fr = []
        for nm, grp in roads.groupby(name_col) if name_col else [("road", roads)]:
            buf = unary_union(grp.geometry.buffer(40 / crs_unit_to_feet(CRS(cfg["crs"]))))
            seg = edge.intersection(buf)
            ln = seg.length * crs_unit_to_feet(CRS(cfg["crs"]))
            if ln > 20:
                label = f"{nm} {grp[type_col].iloc[0]}".strip() if type_col else str(nm)
                fr.append({"road": label, "frontage_ft": round(ln, 0)})
        out["road_frontage"] = sorted(fr, key=lambda d: -d["frontage_ft"])
    b = layers.get("buildings")
    if b is not None and len(b):
        x = gpd.sjoin(b, parcels[[idf, "geometry"]], predicate="intersects")
        cols = [c for c in (idf, "DESCRIPTIO", "Category", "YRBLT", "SFLA", "STORIES", "address", "building_name",
                            "approx_hgt", "square_ft") if c in x.columns]
        out["buildings"] = x[cols].drop_duplicates().to_dict("records")
    return out


# ------------------------------------------------------------------ 4b. restrictions and context
def restrictions_analysis(cfg, parcels, boundary, layers, svc):
    """Historic designation, easements, preserved farmland, utility lines, traffic, school district,
    taxes and septic suitability: things that restrict use or cost money and are easy to miss."""
    idf = cfg["parcels"]["id_field"]
    k = crs_unit_to_feet(CRS(cfg["crs"]))
    total = float(area_acres(boundary.geometry).iloc[0])
    bgeom = boundary.geometry.iloc[0]
    out = {}

    def coverage(role, fields):
        g = layers.get(role)
        if g is None:
            return None
        if len(g) == 0:
            return []
        x = gpd.overlay(boundary[["geometry"]], g, how="intersection", keep_geom_type=True)
        if len(x) == 0:
            return []
        x["acres"] = area_acres(x.geometry)
        cols = [c for c in fields if c in x.columns]
        t = x.groupby(cols, dropna=False)["acres"].sum().reset_index() if cols else x[["acres"]]
        t["pct"] = (100 * t["acres"] / total).round(1)
        t["acres"] = t["acres"].round(3)
        return t.to_dict("records")

    def nearest(role, fields):
        g = layers.get(role)
        if g is None:
            return None
        if len(g) == 0:
            return []
        d = g.geometry.distance(bgeom) * k
        rows = []
        for i in d.sort_values().index[:3]:
            r = {c: g.loc[i, c] for c in fields if c in g.columns}
            r["distance_ft"] = round(float(d[i]), 0)
            rows.append(r)
        return rows

    out["historic"] = coverage("historic", ["RESNAME", "ResType", "NRIS_Refnum", "CertDate", "NARA_URL"])
    for r in out["historic"] or []:
        if r.get("CertDate") is not None:
            r["CertDate"] = str(r["CertDate"])[:4]
    out["historic_local"] = coverage("historic_local", ["name", "designated"])
    out["easements"] = coverage("easements", ["sitename", "esmthldr", "purpose", "duration", "pub_access"])
    out["preserved_farmland"] = coverage("preserved_farmland", ["LOCATION1", "Municipali"])
    out["school"] = coverage("school", ["Name", "Full_Name", "Web_URL"])
    out["transmission"] = nearest("transmission", ["Voltage"])
    out["streams_dep"] = nearest("streams_dep", ["GNIS_NAME", "SEGMENT_NA", "DES_USE_GE", "USE_DESCRI"])
    for r in out["streams_dep"] or []:
        nm = str(r.get("GNIS_NAME") or "").strip()
        seg = str(r.get("SEGMENT_NA") or "").strip()
        junk = ("bulk upload", "correction")        # DEP sometimes stores edit notes in the name fields
        nm = "" if nm == "None" or any(j in nm.lower() for j in junk) else nm
        seg = "" if seg == "None" or any(j in seg.lower() for j in junk) else seg
        r["GNIS_NAME"] = nm or seg or "unnamed stream"
    tr = layers.get("traffic")
    if tr is not None and len(tr):
        near = tr[tr.geometry.distance(bgeom) * k <= 100].copy()
        if "ST_RT_NO" in near.columns:   # numbered state routes only; local-road placeholder codes have no count year
            near = near[near["ST_RT_NO"].astype(str).str.fullmatch(r"\d+") & (pd.to_numeric(near.get("BASE_YR_CL"), errors="coerce").fillna(0) > 0)]
        cols = [c for c in ("ST_RT_NO", "CUR_AADT", "TRK_PCT", "BASE_YR_CL") if c in near.columns]
        out["traffic"] = near[cols].drop_duplicates().sort_values("CUR_AADT", ascending=False).to_dict("records") if len(near) else []
    # taxes and assessment from the parcel export
    tf = cfg["parcels"].get("tax_fields") or []
    af = cfg["parcels"].get("assessment_field")
    if tf and all(c in parcels.columns for c in tf):
        tax = parcels[tf].apply(pd.to_numeric, errors="coerce").fillna(0)
        rows = [{idf: str(r[idf]), "annual_tax_estimate": float(tax.loc[i].sum())} for i, r in parcels.iterrows()]
        if af and af in parcels.columns:
            for row, (_, r) in zip(rows, parcels.iterrows()):
                row["assessed_value"] = float(pd.to_numeric(r[af], errors="coerce") or 0)
        out["taxes"] = {"by_parcel": rows, "annual_total": round(float(tax.sum().sum()), 0),
                        "assessed_total": round(float(pd.to_numeric(parcels[af], errors="coerce").fillna(0).sum()), 0) if af and af in parcels.columns else None}
    # septic suitability from soils, weighted by acres on the property
    soils = layers.get("soils")
    if soils is not None and len(soils) and "septic_rating" in soils.columns:
        x = gpd.overlay(boundary[["geometry"]], soils, how="intersection", keep_geom_type=True)
        x["acres"] = area_acres(x.geometry)
        out["septic"] = {str(k_): round(float(v), 3) for k_, v in x.groupby("septic_rating", dropna=False)["acres"].sum().items()}
        out["basement"] = {str(k_): round(float(v), 3) for k_, v in x.groupby("basement_rating", dropna=False)["acres"].sum().items()}
        if "frost_free_days" in x.columns and x["frost_free_days"].notna().any():
            out["frost_free_days"] = [int(x["frost_free_days"].min()), int(x["frost_free_days"].max())]
    sw = svc.get("sewer_pct")
    out["sewer_coverage_pct"] = round(sum(sw.values()), 1) if sw else (None if sw is None else 0.0)
    return out


# ------------------------------------------------------------------ 5. growing
GROW_CLASSES = [("garden", "#2ca02c"), ("orchard / terrace", "#8bc34a"), ("pasture / meadow", "#d4c25a"),
                ("wet ground", "#7fb3d5"), ("woodlot / steep or shaded", "#8d6e63"), ("existing buildings", "#333333")]


def growing_analysis(cfg, G, parcels, boundary, build, sun_hours, layers, gw):
    """Where could food be grown? Classes by slope, growing-season sun and soil wetness; no setback
    applied because a garden can sit at the property line. Also counts USDA prime farmland."""
    idf = cfg["parcels"]["id_field"]
    prop = G.mask(boundary.geometry)
    jun, mar = sun_hours["jun21"], sun_hours["mar21"]
    soils = layers.get("soils")
    wet = np.zeros(G.shape, dtype=bool)
    prime = np.zeros(G.shape, dtype=bool)
    statewide = np.zeros(G.shape, dtype=bool)
    if soils is not None and len(soils):
        dc = soils.get("drainagecl", pd.Series([""] * len(soils))).fillna("").str.lower()
        hy = soils.get("hydricrating", pd.Series([""] * len(soils))).fillna("")
        wet = G.mask(soils[dc.str.contains("poorly") | (hy == "Yes")].geometry)
        fc = soils.get("farmlndcl", pd.Series([""] * len(soils))).fillna("").str.lower()
        prime = G.mask(soils[fc.str.contains("prime") & ~fc.str.contains("not prime")].geometry)
        statewide = G.mask(soils[fc.str.contains("statewide")].geometry)
    wl = layers.get("wetlands")
    if wl is not None and len(wl):
        wet |= G.mask(wl.geometry)
    bld = layers.get("buildings")
    footprints = G.mask(bld.geometry) if bld is not None and len(bld) else np.zeros(G.shape, dtype=bool)
    ok = prop & ~np.isnan(G.slope) & ~footprints
    sl = G.slope
    garden = ok & ~wet & (sl <= gw.get("garden_max_slope_pct", 8)) & (jun >= gw.get("garden_min_jun_sun_h", 8))
    orchard = ok & ~wet & ~garden & (sl <= gw.get("orchard_max_slope_pct", 20)) & (jun >= gw.get("orchard_min_jun_sun_h", 7))
    pasture = ok & ~wet & ~garden & ~orchard & (sl <= gw.get("pasture_max_slope_pct", 25)) & (jun >= gw.get("pasture_min_jun_sun_h", 6))
    wetg = ok & wet
    wood = ok & ~garden & ~orchard & ~pasture & ~wetg
    classes = {"garden": garden, "orchard / terrace": orchard, "pasture / meadow": pasture,
               "wet ground": wetg, "woodlot / steep or shaded": wood,
               "existing buildings": prop & footprints}
    cls_grid = np.zeros(G.shape, dtype="int16")
    for i, (k, m) in enumerate(classes.items(), 1):
        cls_grid[m] = i
    G.write(cfg["_out"] / "growing_class.tif", np.where(prop, cls_grid, np.nan))

    pid = G.ids(parcels)
    rows = []
    for i, r in parcels.iterrows():
        m = pid == i + 1
        row = {idf: r[idf]}
        for k, cm in classes.items():
            row[k] = round((cm & m).sum() * G.cell_acres, 3)
        rows.append(row)
    by_parcel = pd.DataFrame(rows)
    by_class = pd.DataFrame([{"class": k, "acres": round(m.sum() * G.cell_acres, 3),
                              "pct": round(100 * m.sum() / prop.sum(), 1),
                              "outside_buildable_acres": round((m & ~build).sum() * G.cell_acres, 3),
                              "jun21_sun_h_mean": round(float(jun[m].mean()), 1) if m.any() else None,
                              "mar21_sun_h_mean": round(float(mar[m].mean()), 1) if m.any() else None}
                             for k, m in classes.items()])
    cultivable = garden | orchard
    usable = build | cultivable | pasture
    reg = layers.get("steep_slope_overlay")
    reg_info = {}
    if reg is not None and len(reg):
        rm = G.mask(reg.geometry)
        reg_info = {"regulated_pct_property": round(100 * float((rm & prop).sum()) / prop.sum(), 1),
                    "cultivable_in_regulated_acres": round(float((rm & cultivable).sum() * G.cell_acres), 3),
                    "pasture_in_regulated_acres": round(float((rm & pasture).sum() * G.cell_acres), 3)}
    canopy = layers.get("canopy")
    canopy_info = {}
    if canopy is not None and len(canopy):
        cm = G.mask(canopy.geometry)
        canopy_info = {"canopy_pct_property": round(100 * (cm & prop).sum() / prop.sum(), 1),
                       "garden_under_canopy_acres": round((cm & garden).sum() * G.cell_acres, 3),
                       "cultivable_under_canopy_acres": round((cm & cultivable).sum() * G.cell_acres, 3),
                       "buildable_under_canopy_acres": round((cm & build).sum() * G.cell_acres, 3),
                       "canopy_mean_height_ft": round(float(canopy["avg_height"].mean()), 0) if "avg_height" in canopy else None}
    summary = {"thresholds": gw,
               "garden_acres": by_class.loc[0, "acres"], "orchard_acres": by_class.loc[1, "acres"],
               "pasture_acres": by_class.loc[2, "acres"], "wet_acres": by_class.loc[3, "acres"],
               "woodlot_acres": by_class.loc[4, "acres"],
               "cultivable_acres": round(cultivable.sum() * G.cell_acres, 3),
               "cultivable_outside_buildable_acres": round((cultivable & ~build).sum() * G.cell_acres, 3),
               "usable_acres_build_or_grow_or_graze": round(usable.sum() * G.cell_acres, 3),
               "usable_pct": round(100 * usable.sum() / prop.sum(), 1),
               "prime_farmland_acres": round((prime & prop).sum() * G.cell_acres, 3),
               "statewide_importance_acres": round((statewide & prop).sum() * G.cell_acres, 3),
               "jun21_sun_hours_property_mean": round(float(jun[prop].mean()), 1),
               "garden_jun21_sun_hours_mean": round(float(jun[garden].mean()), 1) if garden.any() else None,
               "canopy": canopy_info, "steep_slope_regulation": reg_info}
    return classes, by_class, by_parcel, summary


def map_growing(cfg, G, parcels, boundary, classes):
    m = cfg.get("maps", {})
    fig, ax = new_map(boundary, m.get("buffer_pct", 0.1))
    add_basemap(ax, parcels.crs, m.get("basemap", True), m.get("basemap_source", "Esri.WorldImagery"))
    handles = []
    for (k, col), (_, msk) in zip(GROW_CLASSES, classes.items()):
        if msk.any():
            G.polygons(msk, parcels.crs).plot(ax=ax, color=col, alpha=0.7, edgecolor="none")
            handles.append(plt.Rectangle((0, 0), 1, 1, color=col, alpha=0.7, label=k))
    add_contours(ax, G.z_ft, G.transform, 10, color="white", lw=0.4, alpha=0.6, label=False)
    parcels.plot(ax=ax, facecolor="none", edgecolor="yellow", linewidth=0.6, linestyle="--")
    boundary.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=2.5)
    ax.legend(handles=handles, loc="upper left", fontsize=8)
    decorate(ax, parcels.crs, "Growing ground: gardens, orchards, pasture (slope, summer sun, soil wetness)")
    out = cfg["_out"] / "map_growing.png"
    fig.savefig(out, dpi=m.get("dpi", 200), bbox_inches="tight"); plt.close(fig); print(f"wrote {out.name}")


# ------------------------------------------------------------------ maps
def map_buildable(cfg, G, parcels, boundary, build, masks, pads):
    m = cfg.get("maps", {})
    fig, ax = new_map(boundary, m.get("buffer_pct", 0.1))
    add_basemap(ax, parcels.crs, m.get("basemap", True), m.get("basemap_source", "Esri.WorldImagery"))
    colors = {"steep": "#d62728", "setback": "#7f7f7f", "flood": "#1f77b4", "stream_buffer": "#17becf",
              "wetland_buffer": "#2ca02c", "drainage_way_buffer": "#9467bd"}
    handles = []
    for name, mask in masks.items():
        if mask.any():
            G.polygons(mask, parcels.crs).plot(ax=ax, color=colors.get(name, "k"), alpha=0.45, edgecolor="none")
            handles.append(plt.Rectangle((0, 0), 1, 1, color=colors.get(name, "k"), alpha=0.45, label=name.replace("_", " ")))
    if build.any():
        G.polygons(build, parcels.crs).plot(ax=ax, color="#ffdd57", alpha=0.75, edgecolor="none")
        handles.append(plt.Rectangle((0, 0), 1, 1, color="#ffdd57", alpha=0.75, label="buildable"))
    if len(pads):
        pads.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=1.5)
        for _, p in pads.iterrows():
            c = p.geometry.representative_point()
            ax.annotate(f"pad {p['pad']}\n{p['acres']:.1f} ac", (c.x, c.y), ha="center", fontsize=8,
                        bbox=dict(boxstyle="round", fc="white", alpha=0.85, lw=0))
    add_contours(ax, G.z_ft, G.transform, 10, color="white", lw=0.4, alpha=0.6, label=False)
    parcels.plot(ax=ax, facecolor="none", edgecolor="yellow", linewidth=0.6, linestyle="--")
    boundary.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=2.5)
    ax.legend(handles=handles, loc="upper left", fontsize=8)
    decorate(ax, parcels.crs, f"Buildable area (slope <= {cfg['evaluation'].get('max_build_slope_pct', 15)}%, "
                               f"{cfg['evaluation'].get('property_line_setback_ft', 50)} ft setback); 10 ft contours")
    out = cfg["_out"] / "map_buildable.png"
    fig.savefig(out, dpi=m.get("dpi", 200), bbox_inches="tight"); plt.close(fig); print(f"wrote {out.name}")


def map_raster(cfg, G, parcels, boundary, arr, title, fname, cmap, vmin=None, vmax=None, label="", prop_only=True):
    m = cfg.get("maps", {})
    fig, ax = new_map(boundary, m.get("buffer_pct", 0.1))
    add_basemap(ax, parcels.crs, m.get("basemap", True), m.get("basemap_source", "Esri.WorldImagery"))
    a = arr.copy()
    if prop_only:
        a[~G.mask(boundary.geometry)] = np.nan
    H, W = G.shape
    extent = (G.transform.c, G.transform.c + W * G.transform.a, G.transform.f + H * G.transform.e, G.transform.f)
    im = ax.imshow(a, extent=extent, cmap=cmap, vmin=vmin, vmax=vmax, alpha=0.8, interpolation="nearest")
    plt.colorbar(im, ax=ax, fraction=0.035, pad=0.01, label=label)
    add_contours(ax, G.z_ft, G.transform, 10, color="black", lw=0.3, alpha=0.5, label=False)
    parcels.plot(ax=ax, facecolor="none", edgecolor="yellow", linewidth=0.6, linestyle="--")
    boundary.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=2.5)
    decorate(ax, parcels.crs, title)
    out = cfg["_out"] / fname
    fig.savefig(out, dpi=m.get("dpi", 200), bbox_inches="tight"); plt.close(fig); print(f"wrote {out.name}")
    return ax


def map_stormwater(cfg, G, parcels, boundary, acc, outlets, paths, ponds, layers):
    m = cfg.get("maps", {})
    fig, ax = new_map(boundary, m.get("buffer_pct", 0.15))
    add_basemap(ax, parcels.crs, m.get("basemap", True), m.get("basemap_source", "Esri.WorldImagery"))
    H, W = G.shape
    extent = (G.transform.c, G.transform.c + W * G.transform.a, G.transform.f + H * G.transform.e, G.transform.f)
    a = np.log10(np.clip(acc, 0.01, None))
    a[acc < 0.25] = np.nan
    im = ax.imshow(a, extent=extent, cmap="Blues", alpha=0.85, interpolation="nearest")
    cb = plt.colorbar(im, ax=ax, fraction=0.035, pad=0.01, label="contributing area (acres, log scale)")
    cb.set_ticks([-0.6, 0, 1, 2]); cb.set_ticklabels(["0.25", "1", "10", "100"])
    add_contours(ax, G.z_ft, G.transform, 10, color="black", lw=0.3, alpha=0.5, label=False)
    if len(ponds):
        ponds.plot(ax=ax, color="magenta", alpha=0.6)
    for role, col in (("streams", "cyan"), ("wetlands", "green")):
        g = layers.get(role)
        if g is not None and len(g):
            g.plot(ax=ax, color=col, linewidth=2, alpha=0.8)
    parcels.plot(ax=ax, facecolor="none", edgecolor="yellow", linewidth=0.6, linestyle="--")
    boundary.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=2.5)
    if len(outlets):
        outlets.plot(ax=ax, color="orange", edgecolor="black", markersize=80, zorder=5)
        for _, o in outlets.iterrows():
            ax.annotate(f"{o['contributing_acres']:.1f} ac", (o.geometry.x, o.geometry.y), xytext=(6, 6),
                        textcoords="offset points", fontsize=8, bbox=dict(boxstyle="round", fc="white", alpha=0.85, lw=0))
    decorate(ax, parcels.crs, "Stormwater: flow accumulation, discharge points (orange), ponding (magenta)")
    out = cfg["_out"] / "map_stormwater.png"
    fig.savefig(out, dpi=m.get("dpi", 200), bbox_inches="tight"); plt.close(fig); print(f"wrote {out.name}")


# ------------------------------------------------------------------ main
def main():
    cfg = load_config()
    ev = cfg.get("evaluation") or {}
    cfg["evaluation"] = ev
    idf = cfg["parcels"]["id_field"]
    parcels = gpd.read_file(property_path(cfg), layer="parcels")
    boundary = gpd.read_file(property_path(cfg), layer="property_boundary")
    if not (cfg["_out"] / "slope_pct.tif").exists():
        sys.exit("run scripts/06_terrain.py first (needs slope_pct.tif)")
    G = Grid(cfg)
    layers = {role: read_role(cfg, role) for role in
              ("wetlands", "floodplain", "streams", "waterbodies", "soils", "zoning", "sewer", "water", "buildings", "roads", "canopy",
               "historic", "historic_local", "easements", "preserved_farmland", "transmission", "traffic", "school",
               "steep_slope_overlay", "streams_dep")}
    lat = float(boundary.to_crs(4326).geometry.iloc[0].centroid.y)
    prop_acres_vec = float(area_acres(boundary.geometry).iloc[0])
    labf = cfg["parcels"].get("label_field") or idf
    label = dict(zip(parcels[idf].astype(str), parcels[labf].astype(str)))

    def addr(df):
        """Add an Address column after the parcel id for markdown tables."""
        if df is None or idf not in df.columns or labf == idf or any(c.lower() == "address" for c in df.columns):
            return df
        df = df.copy()
        df.insert(list(df.columns).index(idf) + 1, "address", df[idf].astype(str).map(label))
        return df

    print("0/5 flow routing")
    routed = fill_and_route(G.z)
    acc_acres = routed[2] * G.cell_acres
    print("1/5 buildable area")
    build, masks, build_parcel, pads, build_sum = buildable_analysis(cfg, G, parcels, boundary, layers, ev, acc_acres)
    print("2/5 sun exposure (shadow casting)")
    sun_hours, aspects, sun_parcel, sun_sum = sun_analysis(cfg, G, parcels, boundary, build, lat)
    print("3/5 stormwater")
    acc, outlets, paths, ponds, soil_rows, storm_sum = stormwater_analysis(cfg, G, parcels, boundary, build, layers, routed)
    print("4/6 services")
    svc = services_analysis(cfg, parcels, boundary, layers)
    print("5/6 restrictions and context")
    restr = restrictions_analysis(cfg, parcels, boundary, layers, svc)
    print("6/6 growing")
    gw = cfg.get("growing") or {}
    grow_classes, grow_class, grow_parcel, grow_sum = growing_analysis(cfg, G, parcels, boundary, build, sun_hours, layers, gw)

    # vectors
    out_gpkg = cfg["_out"] / "evaluation.gpkg"
    if out_gpkg.exists():
        out_gpkg.unlink()
    G.polygons(build, parcels.crs).to_file(out_gpkg, layer="buildable", driver="GPKG")
    for name, msk in masks.items():
        if msk.any():
            G.polygons(msk, parcels.crs).to_file(out_gpkg, layer=f"constraint_{name}", driver="GPKG")
    if len(pads):
        pads.to_file(out_gpkg, layer="building_pads", driver="GPKG")
    if len(outlets):
        outlets.to_file(out_gpkg, layer="discharge_points", driver="GPKG")
    if len(paths):
        paths.to_file(out_gpkg, layer="flow_paths", driver="GPKG")
    if len(ponds):
        ponds.to_file(out_gpkg, layer="ponding", driver="GPKG")
    for k, msk in grow_classes.items():
        if msk.any():
            G.polygons(msk, parcels.crs).to_file(out_gpkg, layer="growing_" + k.split(" ")[0], driver="GPKG")
    print(f"wrote {out_gpkg.name}")

    # maps
    map_buildable(cfg, G, parcels, boundary, build, masks, pads)
    map_raster(cfg, G, parcels, boundary, sun_hours["dec21"], "Direct sun on Dec 21 (hours, terrain shading only)",
               "map_sun_dec21.png", "YlOrRd", 0, sun_sum["dec21_hours_at_flat_unshaded"], "hours")
    map_raster(cfg, G, parcels, boundary, sun_hours["index_dec21"],
               "Winter solar index, Dec 21 (1.0 = flat unshaded ground; slope and aspect included)",
               "map_solar_index_dec21.png", "RdYlBu_r", 0, 1.6, "index")
    map_raster(cfg, G, parcels, boundary, G.slope, "Slope (%)", "map_slope.png", "RdYlGn_r", 0, 40, "slope %")
    map_stormwater(cfg, G, parcels, boundary, acc, outlets, paths, ponds, layers)
    map_growing(cfg, G, parcels, boundary, grow_classes)

    # tables
    grow_class.to_csv(cfg["_out"] / "growing_by_class.csv", index=False)
    grow_parcel.to_csv(cfg["_out"] / "growing_by_parcel.csv", index=False)
    build_parcel.to_csv(cfg["_out"] / "buildable_by_parcel.csv", index=False)
    aspects.to_csv(cfg["_out"] / "aspect_classes.csv", index=False)
    sun_parcel.to_csv(cfg["_out"] / "sun_by_parcel.csv", index=False)
    result = {"listing": cfg["name"], "thresholds": ev, "buildable": build_sum, "sun": sun_sum,
              "stormwater": storm_sum, "services": svc, "growing": grow_sum, "restrictions": restr}
    (cfg["_out"] / "evaluation.json").write_text(json.dumps(result, indent=2, default=str))

    md = [f"# Site evaluation: {cfg['name']}", "",
          f"Property: {prop_acres_vec:.3f} acres (all parcels merged), {len(parcels)} parcels. "
          f"Thresholds: slope <= {ev.get('max_build_slope_pct', 15)}%, setback {ev.get('property_line_setback_ft', 50)} ft, "
          f"stream buffer {ev.get('stream_buffer_ft', 100)} ft, wetland buffer {ev.get('wetland_buffer_ft', 50)} ft.", "",
          "## 1. Buildable area", "",
          f"- **Buildable: {build_sum['buildable_acres']:.3f} acres ({build_sum['buildable_pct']:.1f}% of property)**",
          f"- If slopes up to 25% were accepted: {build_sum['buildable_if_slope_25_acres']:.3f} acres",
          "- Area removed by each constraint (overlapping): " +
          ", ".join(f"{k_} {v:.2f} ac" for k_, v in build_sum["removed_by"].items()), ""]
    if build_sum["pads"]:
        pd_ = pd.DataFrame(build_sum["pads"])
        pd_["parcel"] = pd_["parcel"].astype(str).map(lambda x: label.get(x, x))
        md += ["### Largest contiguous building pads", "", pd_.to_markdown(index=False), ""]
    else:
        md += [f"_No contiguous buildable patch of at least {ev.get('min_building_pad_acres', 0.5)} acres._", ""]
    md += ["### By parcel", "", addr(build_parcel).to_markdown(index=False), "",
           "## 2. Sun exposure", "",
           f"- Latitude {sun_sum['latitude']}. A flat, unshaded site here gets {sun_sum['dec21_hours_at_flat_unshaded']} h of sun on Dec 21.",
           f"- Mean direct sun on Dec 21: {sun_sum['dec21_sun_hours_property_mean']} h over the property, "
           f"{sun_sum['dec21_sun_hours_buildable_mean']} h over the buildable area",
           f"- Mean direct sun Mar 21: {sun_sum['mar21_sun_hours_property_mean']} h; Jun 21: {sun_sum['jun21_sun_hours_property_mean']} h",
           f"- Winter solar index (direct-beam energy relative to flat unshaded ground, Dec 21): "
           f"{sun_sum['dec21_solar_index_property']} over the property, {sun_sum['dec21_solar_index_buildable']} over the buildable area. "
           f"South slopes score above 1, north slopes below.",
           f"- South-facing or flat ground: {sun_sum['south_or_flat_pct']}% of property",
           f"- Buildable ground with at least 4 h of winter sun: {sun_sum['buildable_with_4h_winter_sun_acres']:.3f} acres",
           "- Shading is from terrain only (bare-earth DEM). Tree canopy and neighbouring houses are not modelled.", "",
           "### Aspect", "", aspects.to_markdown(index=False), "",
           "### By parcel", "", addr(sun_parcel).to_markdown(index=False), "",
           "## 3. Stormwater", "",
           f"- Run-on: {storm_sum['runon_from_offsite_acres']:.2f} acres of off-site land drain onto the property",
           f"- Concentrated flow paths (>= {storm_sum['flow_path_threshold_acres']} ac contributing) inside property: "
           f"about {storm_sum['concentrated_flow_path_ft']:.0f} ft",
           f"- Depressions that would pond (> 0.5 ft deep): {storm_sum['ponding_acres']:.3f} acres", ""]
    if storm_sum["outlets"]:
        o = pd.DataFrame(storm_sum["outlets"])
        o["parcel"] = o["parcel"].astype(str).map(lambda x: label.get(x, x))
        md += ["### Where runoff leaves the property", "", o.to_markdown(index=False), ""]
    if storm_sum["soils"]:
        s = storm_sum["soils"]
        md += ["### Soils (SSURGO, dominant component)", "",
               f"- Hydrologic soil groups: " + ", ".join(f"{k} {v:.1f}%" for k, v in s['hydrologic_group_pct'].items()) +
               f" (A and B absorb rain well, C and D shed runoff): **{s['good_infiltration_pct(A/B)']}% absorbs well**",
               f"- Hydric soils: {s['hydric_acres']:.3f} acres; poorly drained: {s['poorly_drained_acres']:.3f} acres",
               f"- Shallowest restrictive layer: {s['min_depth_to_restrictive_cm']} cm "
               f"({(s['min_depth_to_restrictive_cm'] or 0) / 30.48:.1f} ft) below the surface", "",
               soil_rows.to_markdown(index=False) if len(soil_rows) else "", ""]
    md += ["## 4. Growing ground", "",
           f"- Garden-grade ground (slope <= {gw.get('garden_max_slope_pct', 8)}%, >= {gw.get('garden_min_jun_sun_h', 8)} h June sun, soil not wet): "
           f"**{grow_sum['garden_acres']:.3f} acres**",
           f"- Orchard / terrace ground (slope <= {gw.get('orchard_max_slope_pct', 20)}%): {grow_sum['orchard_acres']:.3f} acres; "
           f"pasture / meadow (slope <= {gw.get('pasture_max_slope_pct', 25)}%): {grow_sum['pasture_acres']:.3f} acres; "
           f"wet ground: {grow_sum['wet_acres']:.3f} acres; woodlot: {grow_sum['woodlot_acres']:.3f} acres",
           f"- Cultivable ground (garden + orchard) that is NOT in the buildable area: {grow_sum['cultivable_outside_buildable_acres']:.3f} acres",
           f"- Usable for building, growing or grazing combined: {grow_sum['usable_acres_build_or_grow_or_graze']:.3f} acres ({grow_sum['usable_pct']}%)",
           f"- USDA prime farmland soils: {grow_sum['prime_farmland_acres']:.3f} acres; farmland of statewide importance: {grow_sum['statewide_importance_acres']:.3f} acres",
           f"- Mean June 21 sun over the property: {grow_sum['jun21_sun_hours_property_mean']} h (terrain shading only)", ""]
    if grow_sum.get("steep_slope_regulation"):
        r = grow_sum["steep_slope_regulation"]
        md += [f"- A steep slope regulation covers {r['regulated_pct_property']}% of the property, including "
               f"{r['cultivable_in_regulated_acres']:.3f} acres of the garden/orchard ground and {r['pasture_in_regulated_acres']:.3f} acres "
               f"of the pasture ground; clearing or terracing there needs review", ""]
    if grow_sum.get("canopy"):
        c = grow_sum["canopy"]
        md += [f"- Tree canopy (mapped): covers {c['canopy_pct_property']}% of the property; {c['buildable_under_canopy_acres']:.3f} acres of "
               f"buildable and {c['cultivable_under_canopy_acres']:.3f} acres of garden/orchard ground are under canopy today", ""]
    md += [
           "### By class", "", grow_class.to_markdown(index=False), "",
           "### By parcel", "", addr(grow_parcel).to_markdown(index=False), "",
           "## 5. Zoning, services, access", ""]
    if svc.get("zoning"):
        md += ["### Zoning", "", pd.DataFrame(svc["zoning"]).to_markdown(index=False), ""]
    for key, word in (("sewer_pct", "Public sewer service area"), ("water_pct", "Public water service area")):
        v = svc.get(key)
        if v is not None:
            md.append(f"- {word}: " + (", ".join(f"{k} {x:.1f}%" for k, x in v.items()) + " of the property" if v else "none mapped on the property"))
    md.append("")
    if svc.get("road_frontage"):
        md += ["### Road frontage (boundary within 40 ft of a centerline)", "",
               pd.DataFrame(svc["road_frontage"]).to_markdown(index=False), ""]
    if svc.get("buildings"):
        md += ["### Existing structures", "", addr(pd.DataFrame(svc["buildings"])).to_markdown(index=False), ""]
    md += ["## 6. Restrictions and context", ""]
    R = restr
    def cov_lines(key, label, name_cols):
        rows = R.get(key)
        if rows is None:
            return [f"- {label}: layer not configured for this listing"]
        if not rows:
            return [f"- {label}: none on the property"]
        return [f"- {label}: " + "; ".join(
            f"{' / '.join(str(r[c]) for c in name_cols if c in r and str(r[c]) not in ('None', 'nan', ''))} ({r['acres']:.3f} ac, {r['pct']}%)" for r in rows)]
    md += cov_lines("historic", "National Register historic district or property", ["RESNAME", "ResType", "CertDate"])
    md += cov_lines("historic_local", "Local historic district", ["name", "designated"])
    md += cov_lines("easements", "Conservation easement", ["sitename", "esmthldr", "purpose"])
    md += cov_lines("preserved_farmland", "Preserved farmland", ["LOCATION1"])
    md += cov_lines("school", "School district", ["Full_Name"])
    if R.get("transmission"):
        md.append("- Nearest electric transmission line: " + "; ".join(f"{r.get('Voltage', '')} at {r['distance_ft']:,.0f} ft" for r in R["transmission"][:2]))
    elif R.get("transmission") == []:
        md.append("- Electric transmission lines: none within the search area")
    if R.get("traffic"):
        md.append("- Traffic on adjoining state routes: " + "; ".join(
            f"SR {r.get('ST_RT_NO')} {int(r.get('CUR_AADT') or 0):,} vehicles/day ({r.get('TRK_PCT', '')}% trucks, {r.get('BASE_YR_CL', '')})" for r in R["traffic"]))
    elif R.get("traffic") == []:
        md.append("- Traffic: no state route within 100 ft of the boundary (local roads are not counted)")
    if R.get("streams_dep"):
        s0 = R["streams_dep"][0]
        md.append(f"- Nearest DEP-classified stream: {s0.get('GNIS_NAME') or s0.get('SEGMENT_NA') or 'unnamed'} "
                  f"({s0.get('DES_USE_GE', '')}, {s0.get('USE_DESCRI', '')}) at {s0['distance_ft']:,.0f} ft")
    if R.get("taxes"):
        t = R["taxes"]
        md.append(f"- Assessed value ${t['assessed_total']:,.0f}; estimated annual property tax ${t['annual_total']:,.0f} (county + municipal + school, from the assessment export)")
    if R.get("septic"):
        sep = ", ".join(f"{k_} {v:.3f} ac" for k_, v in sorted(R["septic"].items(), key=lambda kv: -kv[1]))
        bas = ", ".join(f"{k_} {v:.3f} ac" for k_, v in sorted(R["basement"].items(), key=lambda kv: -kv[1]))
        md += [f"- Soil suitability for a septic absorption field: {sep}", f"- Soil suitability for a dwelling with basement: {bas}"]
        if R.get("sewer_coverage_pct") is not None and R["sewer_coverage_pct"] < 100:
            md.append(f"- Public sewer service area covers {R['sewer_coverage_pct']}% of the property, so on-lot sewage (PA Act 537 planning, site testing) applies to the rest")
    if R.get("frost_free_days"):
        md.append(f"- Frost-free growing season (soil survey): {R['frost_free_days'][0]} to {R['frost_free_days'][1]} days")
    md.append("")
    write_md(cfg["_out"] / "evaluation.md", "\n".join(md))


if __name__ == "__main__":
    main()
