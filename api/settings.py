import os

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "TerraSpectra Inference Service"
    version: str = "1.0.0"
    data_root: str = os.getenv("DATA_ROOT", "data")
    artifacts_root: str = os.getenv("ARTIFACTS_ROOT", "artifacts")
    sqlite_db_path: str = os.getenv("SQLITE_DB_PATH", "data/teraraspectra.db")
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    max_upload_mb: int = 50
    default_model: str = "hybrid-v1"


settings = Settings()
