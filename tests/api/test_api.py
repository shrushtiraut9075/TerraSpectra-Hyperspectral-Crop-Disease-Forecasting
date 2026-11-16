import os
import shutil

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.settings import settings
from ml.data.synth import generate_synthetic_scene

client = TestClient(app)

@pytest.fixture(scope="session", autouse=True)
def setup_test_scene():
    test_scene_dir = os.path.join(settings.data_root, "synth_v1", "test_api_scene")
    os.makedirs(test_scene_dir, exist_ok=True)
    generate_synthetic_scene(
        scene_id="test_api_scene",
        output_dir=test_scene_dir,
        height=32,
        width=32,
        bands=24,
        time_steps=2,
        seed=42,
        write_hdf5=False
    )
    yield
    # Cleanup
    shutil.rmtree(test_scene_dir, ignore_errors=True)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "gpu" in data
    assert "version" in data

def test_scene_registration_and_errors():
    # 1. Error: Path traversal rejection (INVALID_RASTER or 422)
    bad_payload = {
        "name": "Hacked",
        "field_id": "hack",
        "acquired_at": "2026-05-01T00:00:00Z",
        "source_ref": "../secret.tif",
        "data_origin": "synthetic"
    }
    res = client.post("/api/v1/scenes", json=bad_payload)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "INVALID_RASTER"

    # 2. Error: SOURCE_NOT_FOUND (404)
    missing_payload = {
        "name": "Missing",
        "field_id": "farm-a",
        "acquired_at": "2026-05-01T00:00:00Z",
        "source_ref": "non_existent/file.tif",
        "data_origin": "synthetic"
    }
    res = client.post("/api/v1/scenes", json=missing_payload)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "SOURCE_NOT_FOUND"

    # 3. Happy path registration
    valid_payload = {
        "name": "Test Field A",
        "field_id": "farm-test",
        "acquired_at": "2026-05-01T10:00:00Z",
        "source_ref": "synth_v1/test_api_scene/t00.tif",
        "data_origin": "synthetic"
    }
    res = client.post("/api/v1/scenes", json=valid_payload)
    assert res.status_code == 201
    scene = res.json()
    assert "id" in scene
    assert scene["name"] == "Test Field A"
    assert scene["acres"] > 0
    assert len(scene["bounds_wgs84"]) == 4

    scene_id = scene["id"]

    # 4. GET /scenes/{scene_id}
    res_get = client.get(f"/api/v1/scenes/{scene_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == scene_id

    # 5. Error: SCENE_NOT_FOUND (404)
    res_fake = client.get("/api/v1/scenes/non-existent-uuid")
    assert res_fake.status_code == 404
    assert res_fake.json()["error"]["code"] == "SCENE_NOT_FOUND"

    # 6. Error: MODEL_NOT_AVAILABLE (400)
    res_bad_model = client.post(f"/api/v1/scenes/{scene_id}/jobs", json={"model": "super-transformer-9000"})
    assert res_bad_model.status_code == 400
    assert res_bad_model.json()["error"]["code"] == "MODEL_NOT_AVAILABLE"

    # 7. Error: RESULT_NOT_READY (409)
    res_not_ready = client.get(f"/api/v1/scenes/{scene_id}/results/latest")
    assert res_not_ready.status_code == 409
    assert res_not_ready.json()["error"]["code"] == "RESULT_NOT_READY"

    # 8. Start valid Job
    res_job = client.post(f"/api/v1/scenes/{scene_id}/jobs", json={"model": "hybrid-v1"})
    assert res_job.status_code == 202
    job_id = res_job.json()["job_id"]

    # 9. GET /jobs/{job_id}
    res_job_status = client.get(f"/api/v1/jobs/{job_id}")
    assert res_job_status.status_code == 200
    assert res_job_status.json()["status"] in ["queued", "running", "succeeded"]

    # 10. Error: JOB_NOT_FOUND (404)
    res_no_job = client.get("/api/v1/jobs/fake-job-id")
    assert res_no_job.status_code == 404
    assert res_no_job.json()["error"]["code"] == "JOB_NOT_FOUND"

    # 11. GET /scenes/{scene_id}/tiles/0/0/0.png (returns valid PNG bytes even when raster not yet ready)
    res_tile = client.get(f"/api/v1/scenes/{scene_id}/tiles/0/0/0.png")
    assert res_tile.status_code == 200
    assert res_tile.headers["content-type"] == "image/png"

