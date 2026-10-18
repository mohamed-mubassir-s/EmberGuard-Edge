"""Hackathon demo authentication helpers (not enterprise-grade)."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from typing import Optional

from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (emberguard-edge/), not the process cwd
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# Session cookie settings for local demo (use HTTPS + Secure cookies before public hosting)
SESSION_COOKIE_NAME = "emberguard_session"
SESSION_MAX_AGE = int(os.getenv("SESSION_MAX_AGE_SECONDS", "28800"))  # 8 hours
SESSION_SECRET = os.getenv("SESSION_SECRET", "")

DEMO_USERNAME = os.getenv("DEMO_USERNAME", "demo")
# Password is never returned by the API; only used for verification.
_DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "")


def _digest(value: str, secret: str) -> bytes:
    """Derive a verification digest using HMAC-SHA256 (constant-time comparable)."""
    return hmac.new(
        secret.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).digest()


def credentials_configured() -> bool:
    return bool(DEMO_USERNAME and _DEMO_PASSWORD and SESSION_SECRET)


def verify_credentials(username: str, password: str) -> bool:
    """Constant-time credential check against demo env values."""
    if not credentials_configured():
        return False
    if not isinstance(username, str) or not isinstance(password, str):
        return False

    user_ok = secrets.compare_digest(
        _digest(username.strip(), SESSION_SECRET),
        _digest(DEMO_USERNAME, SESSION_SECRET),
    )
    pass_ok = secrets.compare_digest(
        _digest(password, SESSION_SECRET),
        _digest(_DEMO_PASSWORD, SESSION_SECRET),
    )
    return user_ok and pass_ok


def session_username(session: dict) -> Optional[str]:
    user = session.get("user")
    return user if isinstance(user, str) and user else None


def auth_error_message() -> str:
    if not credentials_configured():
        return "Server auth is not configured. Set DEMO_USERNAME, DEMO_PASSWORD, and SESSION_SECRET in .env."
    return "Invalid username or password."


def public_path(path: str) -> bool:
    """Paths that do not require an authenticated session."""
    if path in {"/login", "/api/login", "/favicon.ico"}:
        return True
    # Allow only the login page asset path under static (dashboard HTML is protected)
    if path == "/static/login.html":
        return True
    return False
