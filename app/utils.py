from datetime import date, timedelta
from shapely.geometry import shape, Point
import geojson

EUDR_CUTOFF = date(2020, 12, 31)

def parse_geojson(gj: dict):
    obj = geojson.loads(geojson.dumps(gj))
    geom = None
    if isinstance(obj, geojson.FeatureCollection):
        for f in obj.features:
            if f.geometry:
                geom = f.geometry
                break
    elif isinstance(obj, geojson.Feature):
        geom = obj.geometry
    else:
        geom = obj

    geom_shape = shape(geom)
    if isinstance(geom_shape, Point):
        centroid = (geom_shape.x, geom_shape.y)
        bbox = (geom_shape.x, geom_shape.y, geom_shape.x, geom_shape.y)
    else:
        centroid = (geom_shape.centroid.x, geom_shape.centroid.y)
        bbox = geom_shape.bounds
    return geom, centroid, bbox

def date_windows(recent_days: int):
    today = date.today()
    recent_start = today - timedelta(days=recent_days)
    return {
        "eudr_cutoff": EUDR_CUTOFF.isoformat(),
        "recent_start": recent_start.isoformat(),
        "recent_end": today.isoformat(),
    }
