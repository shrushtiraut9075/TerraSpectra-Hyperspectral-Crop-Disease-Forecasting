import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from api.schemas import JobCreate, JobStatus
from api.services.db import get_job, get_scene, save_job, update_job_progress
from api.services.inference_service import execute_inference_worker, thread_pool

router = APIRouter(tags=["jobs"])

SUPPORTED_MODELS = ["hybrid-v1", "cnn3d-v1", "mlp-v1", "cnn2d-v1"]


@router.post("/scenes/{scene_id}/jobs", status_code=status.HTTP_202_ACCEPTED)
def create_job(scene_id: str, payload: JobCreate, background_tasks: BackgroundTasks):
    scene = get_scene(scene_id)
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SCENE_NOT_FOUND",
                "message": f"Scene {scene_id} does not exist",
                "details": None,
            },
        )

    if payload.model not in SUPPORTED_MODELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "MODEL_NOT_AVAILABLE",
                "message": f"Model '{payload.model}' is not supported.",
                "details": None,
            },
        )

    job_id = str(uuid.uuid4())
    job_record = {
        "job_id": job_id,
        "scene_id": scene_id,
        "model": payload.model,
        "horizon_days": payload.horizon_days,
        "tile_size": payload.tile_size,
        "overlap": payload.overlap,
        "status": "queued",
        "progress": 0.0,
        "tiles_done": 0,
        "tiles_total": 0,
        "started_at": datetime.utcnow().isoformat() + "Z",
        "finished_at": None,
        "error": None,
    }
    save_job(job_record)

    # Dispatch to background thread pool off the event loop
    thread_pool.submit(
        execute_inference_worker, job_id, scene_id, payload.tile_size, payload.overlap
    )

    return {"job_id": job_id, "status": "queued"}


@router.get("/jobs/{job_id}", response_model=JobStatus)
def get_job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": f"Job {job_id} not found", "details": None},
        )
    return job


@router.post("/jobs/{job_id}/cancel", status_code=status.HTTP_200_OK)
def cancel_job(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": f"Job {job_id} not found", "details": None},
        )
    if job["status"] in ["queued", "running"]:
        update_job_progress(
            job_id,
            "cancelled",
            job["progress"],
            job["tiles_done"],
            job["tiles_total"],
            error="Cancelled by user",
        )
    return {"job_id": job_id, "status": "cancelled"}
