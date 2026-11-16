import os
import shutil
import uuid
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from rasterio.transform import from_origin

from api.schemas import Scene, SceneCreate
from api.services.db import delete_scene, get_scene, list_scenes, save_scene
from api.settings import settings
from ml.data.readers import HSIReader
from ml.utils.geo import compute_acreage, compute_bounds_wgs84

router = APIRouter(prefix="/scenes", tags=["scenes"])


@router.post("", response_model=Scene, status_code=status.HTTP_201_CREATED)
def register_scene(payload: SceneCreate):
    # Security: Reject path traversal
    if (
        ".." in payload.source_ref
        or payload.source_ref.startswith("/")
        or payload.source_ref.startswith("\\")
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_RASTER",
                "message": "Invalid source_ref path",
                "details": None,
            },
        )

    full_path = os.path.join(settings.data_root, payload.source_ref)
    if not os.path.exists(full_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SOURCE_NOT_FOUND",
                "message": f"Source {payload.source_ref} not found on disk",
                "details": None,
            },
        )

    # Validate raster
    try:
        reader = HSIReader(full_path)
    except ValueError as ve:
        err_msg = str(ve)
        code = "MISSING_CRS" if "CRS" in err_msg else "INVALID_RASTER"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": code, "message": err_msg, "details": None},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_RASTER",
                "message": f"Unreadable raster: {str(e)}",
                "details": None,
            },
        )

    scene_id = str(uuid.uuid4())
    pixel_size_m = 10.0
    if reader.transform:
        pixel_size_m = abs(reader.transform.a)
        bounds = compute_bounds_wgs84(reader.width, reader.height, reader.transform, reader.crs)
    else:
        # Default approximation if transform missing in HDF5
        default_tf = from_origin(362000.0, 2046000.0, pixel_size_m, pixel_size_m)
        bounds = compute_bounds_wgs84(reader.width, reader.height, default_tf, reader.crs)

    acres = compute_acreage(reader.width, reader.height, pixel_size_m)

    scene_obj = {
        "id": scene_id,
        "name": payload.name,
        "field_id": payload.field_id,
        "acquired_at": payload.acquired_at,
        "data_origin": payload.data_origin,
        "source_ref": payload.source_ref,
        "raster": {
            "width": reader.width,
            "height": reader.height,
            "bands": reader.bands,
            "crs": reader.crs,
            "pixel_size_m": pixel_size_m,
        },
        "bounds_wgs84": [round(b, 6) for b in bounds],
        "acres": round(acres, 2),
    }

    save_scene(scene_obj)
    return scene_obj


@router.post("/upload", response_model=Scene, status_code=status.HTTP_201_CREATED)
async def upload_scene(
    name: str = Form(...),
    field_id: str = Form(...),
    acquired_at: str = Form(...),
    data_origin: str = Form("synthetic"),
    file: UploadFile = File(...),
):
    upload_dir = os.path.join(settings.data_root, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    temp_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(upload_dir, temp_filename)

    # Read and check size
    contents = await file.read()
    if len(contents) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "PAYLOAD_TOO_LARGE",
                "message": f"Upload exceeds {settings.max_upload_mb}MB limit",
                "details": None,
            },
        )

    with open(file_path, "wb") as f:
        f.write(contents)

    rel_path = os.path.relpath(file_path, settings.data_root).replace("\\", "/")
    payload = SceneCreate(
        name=name,
        field_id=field_id,
        acquired_at=acquired_at,
        source_ref=rel_path,
        data_origin=data_origin,
    )
    return register_scene(payload)


@router.get("", response_model=List[Scene])
def get_scenes(field_id: Optional[str] = None):
    return list_scenes(field_id)


@router.get("/{scene_id}", response_model=Scene)
def get_single_scene(scene_id: str):
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
    return scene


@router.delete("/{scene_id}", status_code=status.HTTP_200_OK)
def remove_scene(scene_id: str):
    deleted = delete_scene(scene_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SCENE_NOT_FOUND",
                "message": f"Scene {scene_id} does not exist",
                "details": None,
            },
        )
    results_dir = os.path.join(settings.data_root, "results", scene_id)
    if os.path.exists(results_dir):
        shutil.rmtree(results_dir, ignore_errors=True)
    return {"status": "deleted", "scene_id": scene_id}
