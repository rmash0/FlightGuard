"""Env helpers for the prediction services.

Role B owns the shared cache and demo-fixture loader. Until those land,
clients read `DEMO_MODE` and the source URLs themselves.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

_ENV_LOADED = False


def load_env() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    _ENV_LOADED = True


def demo_mode() -> bool:
    load_env()
    return os.getenv("DEMO_MODE", "false").strip().lower() in {"1", "true", "yes"}


def open_meteo_base_url() -> str:
    load_env()
    return os.getenv("OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1/forecast")


def faa_nas_url() -> str:
    load_env()
    return os.getenv(
        "FAA_NAS_URL",
        "https://nasstatus.faa.gov/api/airport-status-information",
    )
