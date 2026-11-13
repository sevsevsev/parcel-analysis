"""Shared map helpers: framing, basemap, scale bar, north arrow, contours."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib_scalebar.scalebar import ScaleBar  # noqa: E402
from pyproj import CRS  # noqa: E402

from _common import crs_unit_to_feet  # noqa: E402


def add_basemap(ax, crs, enabled, source="Esri.WorldImagery"):
    """source is a dotted contextily provider name, e.g. Esri.WorldImagery, Esri.WorldTopoMap,
    CartoDB.Positron. OpenStreetMap.Mapnik blocks automated requests, so avoid it."""
    if not enabled:
        return False
    try:
        import contextily as cx
        prov = cx.providers
        for part in source.split("."):
            prov = prov[part]
        cx.add_basemap(ax, crs=crs, source=prov, attribution_size=6)
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
    ax.add_artist(ScaleBar(1 / k * 0.3048, units="m", location="lower left", box_alpha=0.7))
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
