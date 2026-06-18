"""Application configuration.

Local development falls back to SQLite so the app runs on Fedora without a
local Postgres instance. Production (Docker Compose) injects DATABASE_URL
pointing at the `db` service.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _database_uri() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return f"sqlite:///{BASE_DIR / 'instance' / 'dev.db'}"
    # Route plain postgres URLs through the psycopg3 driver
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = _database_uri()
    # Session hardening
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True

    # Home Assistant integration (mock mode until configured)
    HOME_ASSISTANT_URL = os.environ.get("HOME_ASSISTANT_URL", "")
    HOME_ASSISTANT_TOKEN = os.environ.get("HOME_ASSISTANT_TOKEN", "")
    HOME_ASSISTANT_LIGHTS = os.environ.get("HOME_ASSISTANT_LIGHTS", "")
    HOME_ASSISTANT_SENSOR = os.environ.get("HOME_ASSISTANT_SENSOR", "")

    # Creality K2 Plus integration (mock mode until configured)
    CREALITY_K2_HOST = os.environ.get("CREALITY_K2_HOST", "")
    CREALITY_K2_PORT = os.environ.get("CREALITY_K2_PORT", "7125")
    CREALITY_K2_API_KEY = os.environ.get("CREALITY_K2_API_KEY", "")
    # Optional — Moonraker webcam snapshot URL (auto-detected when helper-script camera is installed)
    CREALITY_K2_CAMERA_SNAPSHOT_URL = os.environ.get("CREALITY_K2_CAMERA_SNAPSHOT_URL", "")
    CREALITY_K2_FLUIDD_URL = os.environ.get("CREALITY_K2_FLUIDD_URL", "")

    # PWA — canonical HTTPS URL (Tailscale Serve) for install prompts on phones
    PWA_CANONICAL_URL = os.environ.get("PWA_CANONICAL_URL", "").rstrip("/")


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"


def get_config():
    env = os.environ.get("FLASK_ENV", "development")
    return ProductionConfig if env == "production" else DevelopmentConfig
