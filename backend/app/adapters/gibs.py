from datetime import datetime, timezone


class GIBSAdapter:
    WMS_BASE = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"

    def __init__(self):
        pass

    async def get_wms_url(
        self, layer: str = "MODIS_Terra_Thermal_Anomalies_375m_All", date: str = None
    ) -> str:
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        params = (
            f"?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0"
            f"&LAYERS={layer}"
            f"&TIME={date}"
        )
        return f"{self.WMS_BASE}{params}"

    async def get_imagery_bbox(
        self,
        north: float,
        south: float,
        east: float,
        west: float,
        date: str = None,
        layer: str = "MODIS_Terra_CorrectedReflectance_TrueColor",
    ) -> str:
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        width = 1024
        height = int(width * (north - south) / (east - west)) if east != west else 1024

        params = (
            f"?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap"
            f"&LAYERS={layer}"
            f"&CRS=EPSG:4326"
            f"&BBOX={south},{west},{north},{east}"
            f"&WIDTH={width}&HEIGHT={height}"
            f"&FORMAT=image/png"
            f"&TIME={date}"
        )
        return f"{self.WMS_BASE}{params}"
