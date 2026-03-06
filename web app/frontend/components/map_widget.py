"""
Responsible for: creating and rendering geemap/folium Map objects.
"""

import ee
import folium
import streamlit as st
import geemap.foliumap as geemap

try:
    from streamlit_folium import st_folium
    _HAS_ST_FOLIUM = True
except ImportError:
    _HAS_ST_FOLIUM = False


class MapWidget:
    """
    Creates geemap Map objects and renders them in Streamlit.

    Usage:
        widget = MapWidget(center_lat, center_lon)
        m = widget.create_base_map(zoom=14)
        widget.add_ee_layer(m, ee_image, vis_params, 'NDVI')
        widget.add_aoi_border(m, aoi)
        widget.render(m, height=540)
    """

    DEFAULT_ZOOM   = 14
    DEFAULT_HEIGHT = 540

    def __init__(self, center_lat: float, center_lon: float):
        self._lat = center_lat
        self._lon = center_lon

    def create_base_map(self, zoom: int = DEFAULT_ZOOM) -> geemap.Map:
        """Return a geemap Map with HYBRID basemap centred on the site."""
        m = geemap.Map(
            center=[self._lat, self._lon],
            zoom=zoom,
            add_google_map=False,
        )
        m.add_basemap('HYBRID')
        return m

    def add_ee_layer(
        self,
        m: geemap.Map,
        image: ee.Image,
        vis_params: dict,
        name: str,
        visible: bool = True,
    ) -> None:
        """Add a single EE image layer to the map."""
        m.addLayer(image, vis_params, name, visible)

    def add_aoi_border(
        self,
        m: geemap.Map,
        aoi: ee.Geometry,
        color: str = '764ba2',
        fill_color: str = '764ba21A',
        width: int = 2,
    ) -> None:
        """Add the area-of-interest boundary as a styled feature layer."""
        styled = ee.FeatureCollection(aoi).style(
            color=color, fillColor=fill_color, width=width
        )
        m.addLayer(styled, {}, 'AOI')

    def add_date_overlay(self, m: geemap.Map, date_str: str, index: int, total: int) -> None:
        """Add a floating date label onto the map HTML."""
        html = f"""
        <div style="position:absolute; top:12px; left:12px; z-index:1000;
                    background:rgba(26,26,46,0.82); color:#f0c040;
                    font-family:monospace; font-size:14px; font-weight:700;
                    padding:6px 12px; border-radius:6px; border:1px solid #764ba2;
                    pointer-events:none; letter-spacing:1px;">
            📅 {date_str} &nbsp; [{index}/{total}]
        </div>
        """
        m.get_root().html.add_child(folium.Element(html))

    def add_draw_control(self, m: geemap.Map) -> None:
        """Add a Folium Draw plugin to allow user polygon/point input."""
        from folium.plugins import Draw
        Draw(export=True).add_to(m)

    def render(
        self,
        m: geemap.Map,
        height: int = DEFAULT_HEIGHT,
        key: str | None = None,
    ) -> dict | None:
        """
        Render the map in the Streamlit page.

        Returns the st_folium output dict if streamlit_folium is available
        (contains drawn geometries etc.), otherwise None.
        """
        m.add_layer_control()
        if _HAS_ST_FOLIUM:
            return st_folium(
                m,
                height=height,
                width='100%',
                returned_objects=['all_drawings'],
                key=key,
            )
        m.to_streamlit(height=height)
        return None