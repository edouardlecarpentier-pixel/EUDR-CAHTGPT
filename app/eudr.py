from pystac_client import Client
import requests
from urllib.parse import quote

S2_COLLECTIONS = ["sentinel-2-l2a"]

class EUDRChecker:
    def __init__(self, stac_endpoint: str, titiler_endpoint: str, max_cloud: int = 20):
        self.stac = Client.open(stac_endpoint)
        self.titiler = titiler_endpoint.rstrip("/")
        self.max_cloud = max_cloud

    def _search_s2(self, bbox, time: str):
        return self.stac.search(
            collections=S2_COLLECTIONS,
            bbox=bbox,
            datetime=time,
            query={"eo:cloud_cover": {"lt": self.max_cloud}},
            sortby=[{"field": "properties.eo:cloud_cover", "direction": "asc"}],
            limit=1,
        )

    def _tilejson_from_item(self, item):
        item_href = item.get_self_href()
        url = f"{self.titiler}/stac/tilejson.json?url={quote(item_href, safe='')}&asset=visual"
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        return r.json()

    def find_best_images(self, bbox, before_2021_end: str, recent_start: str, recent_end: str):
        pre2021_items = list(self._search_s2(bbox, f"../{before_2021_end}").get_items())
        recent_items = list(self._search_s2(bbox, f"{recent_start}/{recent_end}").get_items())

        out = {}
        if pre2021_items:
            pre = pre2021_items[0]
            out["pre2021"] = {
                "id": pre.id,
                "datetime": pre.properties.get("datetime"),
                "cloud": pre.properties.get("eo:cloud_cover"),
                "tile": self._tilejson_from_item(pre),
            }
        if recent_items:
            rec = recent_items[0]
            out["recent"] = {
                "id": rec.id,
                "datetime": rec.properties.get("datetime"),
                "cloud": rec.properties.get("eo:cloud_cover"),
                "tile": self._tilejson_from_item(rec),
            }
        return out

    def google_static_maps(self, lon: float, lat: float, key: str, zoom=16, size="640x640"):
        if not key:
            return None
        return f"https://maps.googleapis.com/maps/api/staticmap?center={lat},{lon}&zoom={zoom}&size={size}&maptype=satellite&key={key}"
