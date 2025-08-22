from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional
import os, json
from utils import parse_geojson, date_windows
from eudr import EUDRChecker
from jinja2 import Environment, FileSystemLoader, select_autoescape

app = FastAPI(title="EUDR Visual Checker API")

env = Environment(
    loader=FileSystemLoader(searchpath="."),
    autoescape=select_autoescape(['html'])
)

STAC_ENDPOINT = os.getenv("STAC_ENDPOINT", "https://earth-search.aws.element84.com/v1")
TITILER_ENDPOINT = os.getenv("TITILER_ENDPOINT", "http://titiler:8000")
RECENT_DAYS = int(os.getenv("RECENT_DAYS", "180"))
MAX_CLOUD = int(os.getenv("MAX_CLOUD", "20"))
GOOGLE_KEY = os.getenv("GOOGLE_STATICMAPS_KEY", "")

checker = EUDRChecker(STAC_ENDPOINT, TITILER_ENDPOINT, max_cloud=MAX_CLOUD)

class CheckResult(BaseModel):
    pre2021: Optional[dict] = None
    recent: Optional[dict] = None
    centroid: tuple
    bbox: tuple
    windows: dict
    google_static: Optional[str] = None

@app.get("/")
def root():
    return {"name": "EUDR Visual Checker API", "docs": "/docs"}

@app.post("/check", response_model=CheckResult)
async def check(geojson_file: UploadFile = File(...)):
    try:
        data = json.loads((await geojson_file.read()).decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"GeoJSON invalide: {e}")

    geom, centroid, bbox = parse_geojson(data)
    windows = date_windows(RECENT_DAYS)

    images = checker.find_best_images(
        bbox=bbox,
        before_2021_end=windows["eudr_cutoff"],
        recent_start=windows["recent_start"],
        recent_end=windows["recent_end"],
    )

    gstatic = checker.google_static_maps(centroid[0], centroid[1], GOOGLE_KEY)

    return JSONResponse(
        {
            **images,
            "centroid": centroid,
            "bbox": bbox,
            "windows": windows,
            "google_static": gstatic,
        }
    )

@app.post("/report", response_class=HTMLResponse)
async def report(geojson_file: UploadFile = File(...)):
    data = json.loads((await geojson_file.read()).decode("utf-8"))
    geom, centroid, bbox = parse_geojson(data)
    windows = date_windows(RECENT_DAYS)

    images = checker.find_best_images(
        bbox=bbox,
        before_2021_end=windows["eudr_cutoff"],
        recent_start=windows["recent_start"],
        recent_end=windows["recent_end"],
    )

    template = env.get_template("app/viewer.html")
    html = template.render(
        centroid_lat=centroid[1],
        centroid_lon=centroid[0],
        geom_json=json.dumps(data),
        pre2021=images.get("pre2021"),
        recent=images.get("recent"),
        windows=windows,
        titiler=TITILER_ENDPOINT,
    )
    return HTMLResponse(html)
