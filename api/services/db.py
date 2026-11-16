import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from api.settings import settings

_db_initialized = False


def get_db_connection() -> sqlite3.Connection:
    global _db_initialized
    os.makedirs(os.path.dirname(settings.sqlite_db_path), exist_ok=True)
    conn = sqlite3.connect(settings.sqlite_db_path)
    conn.row_factory = sqlite3.Row
    if not _db_initialized:
        _db_initialized = True
        init_db()
    return conn


def init_db() -> None:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scenes (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        field_id TEXT NOT NULL,
        acquired_at TEXT NOT NULL,
        data_origin TEXT NOT NULL,
        source_ref TEXT NOT NULL,
        raster_json TEXT NOT NULL,
        bounds_json TEXT NOT NULL,
        acres REAL NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        job_id TEXT PRIMARY KEY,
        scene_id TEXT NOT NULL,
        model TEXT NOT NULL,
        horizon_days INTEGER NOT NULL,
        tile_size INTEGER NOT NULL,
        overlap INTEGER NOT NULL,
        status TEXT NOT NULL,
        progress REAL NOT NULL,
        tiles_done INTEGER NOT NULL,
        tiles_total INTEGER NOT NULL,
        started_at TEXT,
        finished_at TEXT,
        error TEXT,
        FOREIGN KEY (scene_id) REFERENCES scenes(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fields (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        crop_type TEXT NOT NULL,
        acres REAL NOT NULL,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        bounds_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    # Server restart recovery: Any job left 'running' becomes 'failed'
    cursor.execute(
        """
    UPDATE jobs
    SET status = 'failed', error = 'Server restarted while job was running', finished_at = ?
    WHERE status = 'running'
    """,
        (datetime.utcnow().isoformat() + "Z",),
    )

    seed_default_scenes(cursor)

    conn.commit()
    conn.close()


def seed_default_scenes(cursor: sqlite3.Cursor) -> None:
    now = datetime.utcnow().isoformat() + "Z"

    # Always ensure default fields exist in fields table
    cursor.execute("SELECT count(*) FROM fields")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            """
        INSERT OR REPLACE INTO fields (id, name, crop_type, acres, lat, lon, bounds_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                "farm-a",
                "Farm Alpha (1,000 Acres, Pune UTM-43N)",
                "Sugarcane",
                988.42,
                18.491,
                73.7023,
                json.dumps([73.692781, 18.481887, 73.711858, 18.500088]),
                now,
            ),
        )
        cursor.execute(
            """
        INSERT OR REPLACE INTO fields (id, name, crop_type, acres, lat, lon, bounds_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                "farm-b",
                "Farm Beta (650 Acres, Vineyard)",
                "Grapes",
                988.42,
                18.491,
                73.726,
                json.dumps([73.716458, 18.482049, 73.735533, 18.500248]),
                now,
            ),
        )

    # Check if farm-a scenes already exist
    cursor.execute("SELECT count(*) FROM scenes WHERE field_id = 'farm-a'")
    if cursor.fetchone()[0] > 0:
        return

    dates = [
        "2026-05-01T10:00:00Z",
        "2026-05-08T10:00:00Z",
        "2026-05-15T10:00:00Z",
        "2026-05-22T10:00:00Z",
        "2026-05-29T10:00:00Z",
        "2026-06-05T10:00:00Z",
        "2026-06-12T10:00:00Z",
        "2026-06-19T10:00:00Z",
    ]
    now = datetime.utcnow().isoformat() + "Z"

    # Register 8 acquisitions for farm-a
    for t in range(8):
        s_id = f"scene_000_t0{t}"
        source_ref = f"raw/synth_v1/scene_000/t0{t}.tif"
        raster_meta = {
            "width": 200,
            "height": 200,
            "bands": 224,
            "crs": "EPSG:32643",
            "pixel_size_m": 10.0,
        }
        bounds = [73.692781, 18.481887, 73.711858, 18.500088]
        acres = 988.42

        cursor.execute(
            """
        INSERT OR REPLACE INTO scenes (id, name, field_id, acquired_at, data_origin, source_ref, raster_json, bounds_json, acres, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                s_id,
                f"Farm Alpha - Acq #{t + 1}",
                "farm-a",
                dates[t],
                "synthetic",
                source_ref,
                json.dumps(raster_meta),
                json.dumps(bounds),
                acres,
                now,
            ),
        )

        cursor.execute(
            """
        INSERT OR REPLACE INTO jobs (job_id, scene_id, model, horizon_days, tile_size, overlap, status, progress, tiles_done, tiles_total, started_at, finished_at, error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                f"job-seed-{s_id}",
                s_id,
                "hybrid-v1",
                21,
                256,
                32,
                "succeeded",
                1.0,
                100,
                100,
                dates[t],
                dates[t],
                None,
            ),
        )

    # Also register scene_000 pointing to latest acquisition t07
    cursor.execute(
        """
    INSERT OR REPLACE INTO scenes (id, name, field_id, acquired_at, data_origin, source_ref, raster_json, bounds_json, acres, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "scene_000",
            "Farm Alpha - Latest Survey",
            "farm-a",
            dates[7],
            "synthetic",
            "raw/synth_v1/scene_000/t07.tif",
            json.dumps(
                {
                    "width": 200,
                    "height": 200,
                    "bands": 224,
                    "crs": "EPSG:32643",
                    "pixel_size_m": 10.0,
                }
            ),
            json.dumps([73.692781, 18.481887, 73.711858, 18.500088]),
            988.42,
            now,
        ),
    )
    cursor.execute(
        """
    INSERT OR REPLACE INTO jobs (job_id, scene_id, model, horizon_days, tile_size, overlap, status, progress, tiles_done, tiles_total, started_at, finished_at, error)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            "job-seed-scene_000",
            "scene_000",
            "hybrid-v1",
            21,
            256,
            32,
            "succeeded",
            1.0,
            100,
            100,
            dates[7],
            dates[7],
            None,
        ),
    )

    # Register farm-b (scene_001)
    for t in range(8):
        s_id = f"scene_001_t0{t}"
        source_ref = f"raw/synth_v1/scene_001/t0{t}.tif"
        raster_meta = {
            "width": 200,
            "height": 200,
            "bands": 224,
            "crs": "EPSG:32643",
            "pixel_size_m": 10.0,
        }
        bounds = [73.716458, 18.482049, 73.735533, 18.500248]
        acres = 988.42
        cursor.execute(
            """
        INSERT OR REPLACE INTO scenes (id, name, field_id, acquired_at, data_origin, source_ref, raster_json, bounds_json, acres, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                s_id,
                f"Farm Beta - Acq #{t + 1}",
                "farm-b",
                dates[t],
                "synthetic",
                source_ref,
                json.dumps(raster_meta),
                json.dumps(bounds),
                acres,
                now,
            ),
        )


    # Register default fields in fields table
    cursor.execute("""
    INSERT OR REPLACE INTO fields (id, name, crop_type, acres, lat, lon, bounds_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "farm-a",
        "Farm Alpha (Pune UTM-43N)",
        "Sugarcane",
        988.42,
        18.491,
        73.7023,
        json.dumps([73.692781, 18.481887, 73.711858, 18.500088]),
        now
    ))
    cursor.execute("""
    INSERT OR REPLACE INTO fields (id, name, crop_type, acres, lat, lon, bounds_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "farm-b",
        "Farm Beta (Punjab Wheat Belt)",
        "Wheat",
        988.42,
        31.514,
        74.872,
        json.dumps([73.716458, 18.482049, 73.735533, 18.500248]),
        now
    ))


def save_field(field_dict: Dict[str, Any]) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
    INSERT OR REPLACE INTO fields (id, name, crop_type, acres, lat, lon, bounds_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            field_dict["id"],
            field_dict["name"],
            field_dict.get("crop_type", "Sugarcane"),
            field_dict["acres"],
            field_dict["lat"],
            field_dict["lon"],
            json.dumps(field_dict["bounds_wgs84"]),
            field_dict.get("created_at", datetime.utcnow().isoformat() + "Z"),
        ),
    )
    conn.commit()
    conn.close()


def list_fields() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM fields ORDER BY created_at ASC")
    rows = cursor.fetchall()
    conn.close()
    result = []
    for row in rows:
        result.append(
            {
                "id": row["id"],
                "name": row["name"],
                "crop_type": row["crop_type"],
                "acres": row["acres"],
                "lat": row["lat"],
                "lon": row["lon"],
                "bounds_wgs84": tuple(json.loads(row["bounds_json"])),
                "created_at": row["created_at"],
            }
        )
    return result


def get_field(field_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM fields WHERE id = ?", (field_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row["id"],
        "name": row["name"],
        "crop_type": row["crop_type"],
        "acres": row["acres"],
        "lat": row["lat"],
        "lon": row["lon"],
        "bounds_wgs84": tuple(json.loads(row["bounds_json"])),
        "created_at": row["created_at"],
    }


def save_scene(scene_dict: Dict[str, Any]) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
    INSERT OR REPLACE INTO scenes (id, name, field_id, acquired_at, data_origin, source_ref, raster_json, bounds_json, acres, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            scene_dict["id"],
            scene_dict["name"],
            scene_dict["field_id"],
            scene_dict["acquired_at"],
            scene_dict["data_origin"],
            scene_dict["source_ref"],
            json.dumps(scene_dict["raster"]),
            json.dumps(scene_dict["bounds_wgs84"]),
            scene_dict["acres"],
            datetime.utcnow().isoformat() + "Z",
        ),
    )
    conn.commit()
    conn.close()


def get_scene(scene_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row["id"],
        "name": row["name"],
        "field_id": row["field_id"],
        "acquired_at": row["acquired_at"],
        "data_origin": row["data_origin"],
        "source_ref": row["source_ref"],
        "raster": json.loads(row["raster_json"]),
        "bounds_wgs84": tuple(json.loads(row["bounds_json"])),
        "acres": row["acres"],
    }


def list_scenes(field_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    if field_id:
        cursor.execute(
            "SELECT * FROM scenes WHERE field_id = ? ORDER BY acquired_at ASC", (field_id,)
        )
    else:
        cursor.execute("SELECT * FROM scenes ORDER BY acquired_at ASC")
    rows = cursor.fetchall()
    conn.close()
    scenes = []
    for row in rows:
        scenes.append(
            {
                "id": row["id"],
                "name": row["name"],
                "field_id": row["field_id"],
                "acquired_at": row["acquired_at"],
                "data_origin": row["data_origin"],
                "source_ref": row["source_ref"],
                "raster": json.loads(row["raster_json"]),
                "bounds_wgs84": tuple(json.loads(row["bounds_json"])),
                "acres": row["acres"],
            }
        )
    return scenes


def delete_scene(scene_id: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM scenes WHERE id = ?", (scene_id,))
    cursor.execute("DELETE FROM jobs WHERE scene_id = ?", (scene_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def save_job(job_dict: Dict[str, Any]) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
    INSERT OR REPLACE INTO jobs (job_id, scene_id, model, horizon_days, tile_size, overlap, status, progress, tiles_done, tiles_total, started_at, finished_at, error)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            job_dict["job_id"],
            job_dict["scene_id"],
            job_dict.get("model", "hybrid-v1"),
            job_dict.get("horizon_days", 21),
            job_dict.get("tile_size", 256),
            job_dict.get("overlap", 32),
            job_dict["status"],
            job_dict.get("progress", 0.0),
            job_dict.get("tiles_done", 0),
            job_dict.get("tiles_total", 0),
            job_dict.get("started_at"),
            job_dict.get("finished_at"),
            job_dict.get("error"),
        ),
    )
    conn.commit()
    conn.close()


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)


def update_job_progress(
    job_id: str, status: str, progress: float, done: int, total: int, error: Optional[str] = None
):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat() + "Z"
    fin = now if status in ["succeeded", "failed", "cancelled"] else None
    cursor.execute(
        """
    UPDATE jobs
    SET status = ?, progress = ?, tiles_done = ?, tiles_total = ?, finished_at = COALESCE(?, finished_at), error = ?
    WHERE job_id = ?
    """,
        (status, progress, done, total, fin, error, job_id),
    )
    conn.commit()
    conn.close()


def get_latest_successful_job(scene_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
    SELECT * FROM jobs
    WHERE scene_id = ? AND status = 'succeeded'
    ORDER BY finished_at DESC LIMIT 1
    """,
        (scene_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
