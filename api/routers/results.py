import json
import os

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import FileResponse

from api.schemas import LatestResults
from api.services.db import get_latest_successful_job, get_scene
from api.services.inference_service import generate_tile_png
from api.settings import settings

router = APIRouter(prefix="/scenes", tags=["results"])


@router.get("/{scene_id}/results/latest", response_model=LatestResults)
def get_latest_results(scene_id: str):
    scene = get_scene(scene_id)
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SCENE_NOT_FOUND",
                "message": f"Scene {scene_id} not found",
                "details": None,
            },
        )

    results_dir = os.path.join(settings.data_root, "results", scene_id)
    risk_tif = os.path.join(results_dir, "risk.tif")

    job = get_latest_successful_job(scene_id)
    if not os.path.exists(risk_tif):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "RESULT_NOT_READY",
                "message": "Inference has not completed for this scene.",
                "details": None,
            },
        )

    job_id = job["job_id"] if job else "default"
    model = job["model"] if job else "hybrid-v1"
    horizon_days = job["horizon_days"] if job else 21

    return {
        "job_id": job_id,
        "risk_raster_url": f"/api/v1/scenes/{scene_id}/results/risk.tif",
        "tiles_url_template": f"/api/v1/scenes/{scene_id}/tiles/{{z}}/{{x}}/{{y}}.png",
        "zones_url": f"/api/v1/scenes/{scene_id}/results/zones.geojson",
        "model": model,
        "horizon_days": horizon_days,
        "bounds_wgs84": scene["bounds_wgs84"],
    }


@router.get("/{scene_id}/results/risk.tif")
def get_risk_raster_file(scene_id: str):
    risk_tif = os.path.join(settings.data_root, "results", scene_id, "risk.tif")
    if not os.path.exists(risk_tif):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "RESULT_NOT_READY",
                "message": "Risk raster not ready.",
                "details": None,
            },
        )
    return FileResponse(
        risk_tif,
        media_type="image/tiff",
        filename=f"risk_{scene_id}.tif",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/{scene_id}/results/zones.geojson")
def get_zones_geojson(scene_id: str, threshold: float = 0.5, min_area_acres: float = 0.5):
    zones_file = os.path.join(settings.data_root, "results", scene_id, "zones.geojson")
    if not os.path.exists(zones_file):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "RESULT_NOT_READY",
                "message": "Risk zones not generated.",
                "details": None,
            },
        )
    with open(zones_file, "r") as f:
        data = json.load(f)

    # Filter features by min_area_acres and threshold if requested
    filtered_features = [
        feat
        for feat in data.get("features", [])
        if feat["properties"].get("area_acres", 0) >= min_area_acres
        and feat["properties"].get("mean_risk", 0) >= threshold
    ]
    data["features"] = filtered_features

    return Response(
        content=json.dumps(data),
        media_type="application/geo+json",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/{scene_id}/tiles/{z}/{x}/{y}.png")
def get_xyz_tile(scene_id: str, z: int, x: int, y: int, threshold: float = 0.5, cmap: str = "risk"):
    png_bytes = generate_tile_png(scene_id, z, x, y, threshold=threshold, cmap=cmap)
    return Response(
        content=png_bytes, media_type="image/png", headers={"Cache-Control": "public, max-age=3600"}
    )
