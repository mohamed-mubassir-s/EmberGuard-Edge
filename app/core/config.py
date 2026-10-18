"""Core configuration for EmberGuard Edge."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
_DEMO_CONFIG = _CONFIG_DIR / "demo_config.json"


def _load_demo_defaults() -> dict:
    """Load demo defaults from JSON config file."""
    if _DEMO_CONFIG.exists():
        with open(_DEMO_CONFIG, "r") as f:
            return json.load(f)
    return {}


_DEMO = _load_demo_defaults()
_THRESH = _DEMO.get("thresholds", {})
_TIMING = _DEMO.get("timings", {})
_BLYNK = _DEMO.get("blynk", {})


class Settings(BaseSettings):
    """Application settings — loaded from env / .env / demo_config.json."""

    # --- Server ---
    host: str = "127.0.0.1"
    port: int = 8000

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./emberguard.db"

    # --- Serial (optional) ---
    serial_port: str = ""
    serial_baud: int = 115200

    # --- Thresholds (DEMO DEFAULTS — not calibrated) ---
    smoke_watch_level: float = _THRESH.get("smoke_watch_level", 300)
    smoke_critical_level: float = _THRESH.get("smoke_critical_level", 600)
    temp_watch_c: float = _THRESH.get("temp_watch_c", 45.0)
    temp_critical_c: float = _THRESH.get("temp_critical_c", 65.0)
    flame_active_level: int = _THRESH.get("flame_active_level", 1)

    # --- Timings ---
    sample_period_ms: int = _TIMING.get("sample_period_ms", 1000)
    log_reading_every_n: int = _TIMING.get("log_reading_every_n", 2)
    watch_persist_ms: int = _TIMING.get("watch_persist_ms", 5000)
    clear_hold_ms: int = _TIMING.get("clear_hold_ms", 5000)
    fault_fail_count: int = _TIMING.get("fault_fail_count", 3)
    fault_clear_count: int = _TIMING.get("fault_clear_count", 3)
    smoke_warmup_ms: int = _TIMING.get("smoke_warmup_ms", 0)

    # --- Blynk (optional) ---
    blynk_min_interval_ms: int = _BLYNK.get("min_interval_ms", 1000)
    blynk_periodic_ms: int = _BLYNK.get("periodic_ms", 10000)
    http_timeout_ms: int = _BLYNK.get("http_timeout_ms", 5000)
    net_queue_len: int = _BLYNK.get("net_queue_len", 8)

    # --- Logging ---
    log_level: str = "INFO"

    # --- Calibration flag ---
    calibrated: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


# Singleton
settings = Settings()
