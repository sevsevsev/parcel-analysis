"""Maps: static PNGs (parcels, property boundary, each overlay) and an interactive HTML map."""
import sys
import warnings
from pathlib import Path

import folium
import geopandas as gpd

sys.path.insert(0, str(Path(__file__).parent))
from _common import area_acres, load_config, property_path  # noqa: E402
from _maps import add_basemap, decorate, frame, label_parcels, plt  # noqa: E402

warnings.filterwarnings("ignore")


def static_map(cfg, parcels, boundary, overlay=None, overlay_name=None, class_field=None):
    m = cfg.get("maps", {})
    idf = cfg["parcels"]["id_field"]
    lab = cfg["parcels"].get("label_field") or idf
    fig, ax = plt.subplots(figsize=(10, 10))
    frame(ax, boundary, m.get("buffer_pct", 0.1))
    if overlay is not None and len(overlay):
        if class_field and class_field in overlay.columns:
            overlay.plot(ax=ax, column=class_field, categorical=True, legend=True, alpha=0.6,
                         edgecolor="none", legend_kwds={"loc": "upper left", "fontsize": 8, "title": class_field})
        else:
            overlay.plot(ax=ax, color="tab:blue", alpha=0.5, edgecolor="none")
    parcels.plot(ax=ax, facecolor="none" if overlay is not None else "#f4e3a1",
                 alpha=1 if overlay is not None else 0.5, edgecolor="#555", linewidth=0.8)
    boundary.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=2.5)
    parcels.plot(ax=ax, facecolor="none", edgecolor="yellow", linewidth=0.6, linestyle="--")
    label_parcels(ax, parcels, lab, fontsize=10)
    add_basemap(ax, parcels.crs, m.get("basemap", True), m.get("basemap_source", "Esri.WorldImagery"))
    acres = float(area_acres(boundary.geometry).iloc[0])
    title = f"Property parcels ({len(parcels)} parcels, {acres:.2f} ac)" if overlay is None \
        else f"{overlay_name} overlay"
    decorate(ax, parcels.crs, title)
    name = "map_parcels.png" if overlay is None else f"map_overlay_{overlay_name}.png"
    out = cfg["_out"] / name
    fig.savefig(out, dpi=m.get("dpi", 200), bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out.relative_to(cfg['_root'])}")


def interactive_map(cfg, parcels, boundary, overlays):
    idf = cfg["parcels"]["id_field"]
    p84, b84 = parcels.to_crs(4326), boundary.to_crs(4326)
    c = b84.geometry.union_all().centroid
    fmap = folium.Map(location=[c.y, c.x], zoom_start=16, tiles=None)
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(fmap)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery", name="Esri imagery").add_to(fmap)
    pcols = [c for c in parcels.columns if c != "geometry"][:12]
    p84["acres"] = area_acres(parcels.geometry).round(3)
    folium.GeoJson(p84, name="Parcels",
                   style_function=lambda f: {"color": "#444", "weight": 1, "fillColor": "#f4e3a1", "fillOpacity": 0.3},
                   tooltip=folium.GeoJsonTooltip(fields=[idf, "acres"]),
                   popup=folium.GeoJsonPopup(fields=pcols + ["acres"])).add_to(fmap)
    for name, gdf, cls in overlays:
        if not len(gdf):
            continue
        g = gdf.to_crs(4326)
        fields = [cls] if cls and cls in g.columns else []
        folium.GeoJson(g, name=name, show=False,
                       style_function=lambda f: {"color": "#1f77b4", "weight": 1, "fillOpacity": 0.4},
                       tooltip=folium.GeoJsonTooltip(fields=fields) if fields else None).add_to(fmap)
    folium.GeoJson(b84, name="Property boundary",
                   style_function=lambda f: {"color": "red", "weight": 3, "fill": False}).add_to(fmap)
    folium.LayerControl(collapsed=False).add_to(fmap)
    fmap.fit_bounds([[b84.total_bounds[1], b84.total_bounds[0]], [b84.total_bounds[3], b84.total_bounds[2]]])
    out = cfg["_out"] / "map_interactive.html"
    fmap.save(out)
    print(f"wrote {out.relative_to(cfg['_root'])}")


def main():
    cfg = load_config()
    parcels = gpd.read_file(property_path(cfg), layer="parcels")
    boundary = gpd.read_file(property_path(cfg), layer="property_boundary")
    static_map(cfg, parcels, boundary)
    ov_gpkg = cfg["_out"] / "overlays.gpkg"
    overlays = []
    for spec in cfg.get("overlays") or []:
        if not ov_gpkg.exists():
            break
        try:
            g = gpd.read_file(ov_gpkg, layer=spec["name"])
        except Exception:
            continue
        overlays.append((spec["name"], g, spec.get("class_field")))
        static_map(cfg, parcels, boundary, g, spec["name"], spec.get("class_field"))
    interactive_map(cfg, parcels, boundary, overlays)


if __name__ == "__main__":
    main()
