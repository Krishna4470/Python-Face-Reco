from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os

class Settings(BaseSettings):
    API_SECRET_KEY: str = "change_this_secret"
    MATCH_THRESHOLD: float = 0.55
    MAX_UPLOAD_SIZE_MB: int = 10
    DATABASE_URL: str = "sqlite:///./data/faces.db"
    ALLOWED_ORIGINS: str = ""

    # Liveness Configuration
    REQUIRE_LIVENESS: bool = True
    LIVENESS_CHALLENGE: str = "blink"
    REQUIRED_BLINKS: int = 1
    LIVENESS_EAR_CLOSED_THRESHOLD: float = 0.20
    LIVENESS_EAR_OPEN_THRESHOLD: float = 0.24
    MIN_LIVENESS_FRAMES: int = 8
    MAX_LIVENESS_FRAMES: int = 30
    MAX_LIVENESS_DURATION_SECONDS: int = 10
    LIVENESS_FACE_MATCH_THRESHOLD: float = 0.60
    LIVENESS_MAX_ATTEMPTS_PER_MINUTE: int = 10

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> List[str]:
        if not self.ALLOWED_ORIGINS:
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

settings = Settings()

# Ensure data directory exists if using sqlite
if settings.DATABASE_URL.startswith("sqlite"):
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
