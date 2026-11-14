"""Shared map helpers: framing, basemap, scale bar, north arrow, contours."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib_scalebar.scalebar import ScaleBar  # noqa: E402
from pyproj import CRS  # noqa: E402

from _common import crs_unit_to_feet  # noqa: E402


_BASEMAP_MEM = {}


def _basemap_image(crs, extent, source):
    """Fetch tiles for `extent` (in `crs`) once, warp them to `crs` once, and cache the result in
    memory and on disk. Warping is the expensive part of drawing an imagery backdrop; every map
    of a listing uses the same frame, so one warp serves them all."""
    import numpy as np
    import contextily as cx
    from pathlib import Path as _P
    root = _P(__file__).resolve().parents[1]
    tile_dir = root / "data" / "cache" / "_tiles"
    tile_dir.mkdir(parents=True, exist_ok=True)
    cx.set_cache_dir(str(tile_dir))
    key = (str(crs), source, tuple(round(v, -1) for v in extent))
    if key in _BASEMAP_MEM:
        return _BASEMAP_MEM[key]
    disk = root / "data" / "cache" / "_shared" / "basemap"
    disk.mkdir(parents=True, exist_ok=True)
    fname = disk / (f"{source}_{str(crs).replace(':', '')}_" + "_".join(str(int(v)) for v in key[2]) + ".npz")
    if fname.exists():
        z = np.load(fname)
        _BASEMAP_MEM[key] = (z["img"], tuple(z["ext"]), str(z["attr"]))
        return _BASEMAP_MEM[key]
    prov = cx.providers
    for part in source.split("."):
        prov = prov[part]
    import geopandas as gpd
    from shapely.geometry import box
    # extent in the map CRS -> Web Mercator bounds for the tile request
    b = gpd.GeoSeries([box(*extent)], crs=crs).to_crs(3857).total_bounds
    img, ext = cx.bounds2img(b[0], b[1], b[2], b[3], ll=False, source=prov, zoom="auto")
    img, ext = cx.warp_tiles(img, ext, t_crs=str(crs))
    attr = prov.get("attribution", "")
    np.savez_compressed(fname, img=img, ext=np.array(ext), attr=attr)
    _BASEMAP_MEM[key] = (img, tuple(ext), attr)
    return _BASEMAP_MEM[key]


def add_basemap(ax, crs, enabled, source="Esri.WorldImagery"):
    """source is a dotted contextily provider name, e.g. Esri.WorldImagery, Esri.WorldTopoMap,
    CartoDB.Positron. OpenStreetMap.Mapnik blocks automated requests, so avoid it."""
    if not enabled:
        return False
    try:
        xmin, xmax = ax.get_xlim()
        ymin, ymax = ax.get_ylim()
        img, ext, attr = _basemap_image(crs, (xmin, ymin, xmax, ymax), source)
        ax.imshow(img, extent=ext, interpolation="bilinear", zorder=-10)
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        if attr:
            ax.text(0.005, 0.005, attr, transform=ax.transAxes, fontsize=6, color="white", alpha=0.9,
                    bbox=dict(boxstyle="square,pad=0.2", fc="black", alpha=0.35, lw=0), wrap=True)
        return True
    except Exception as e:  # noqa: BLE001  offline or blocked: draw without a basemap
        print(f"basemap skipped: {type(e).__name__}: {e}")
        return False


def frame(ax, boundary, pct):
    minx, miny, maxx, maxy = boundary.total_bounds
    w, h = maxx - minx, maxy - miny
    pad = max(w, h) * pct
    ax.set_xlim(minx - pad, maxx + pad)
    ax.set_ylim(miny - pad, maxy + pad)


def decorate(ax, crs, title):
    k = crs_unit_to_feet(CRS(crs))
    ax.add_artist(ScaleBar(1 / k * 0.3048, units="m", location="lower right", box_alpha=0.8, pad=0.6))
    ax.annotate("N", xy=(0.95, 0.93), xycoords="axes fraction", ha="center", fontsize=12, fontweight="bold")
    ax.annotate("", xy=(0.95, 0.92), xytext=(0.95, 0.85), xycoords="axes fraction",
                arrowprops=dict(arrowstyle="-|>", lw=1.5))
    ax.set_title(title)
    ax.set_axis_off()


def label_parcels(ax, parcels, field, fontsize=9):
    for _, r in parcels.iterrows():
        p = r.geometry.representative_point()
        ax.annotate(str(r[field]), (p.x, p.y), ha="center", va="center", fontsize=fontsize, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.25", fc="white", alpha=0.8, lw=0))


def add_contours(ax, dem, transform, interval, z_scale=1.0, color="white", lw=0.5, alpha=0.8, label=True):
    """Draw contours from a DEM array (rasterio transform). interval in output units after z_scale."""
    h, w = dem.shape
    xs = transform.c + (np.arange(w) + 0.5) * transform.a
    ys = transform.f + (np.arange(h) + 0.5) * transform.e
    z = dem * z_scale
    lo, hi = np.nanmin(z), np.nanmax(z)
    levels = np.arange(np.floor(lo / interval) * interval, hi + interval, interval)
    cs = ax.contour(xs, ys, z, levels=levels, colors=color, linewidths=lw, alpha=alpha)
    if label:
        ax.clabel(cs, fontsize=6, fmt="%d", inline=True)
    return cs


def new_map(boundary, pct=0.1, size=(10, 10)):
    fig, ax = plt.subplots(figsize=size)
    frame(ax, boundary, pct)
    return fig, ax
