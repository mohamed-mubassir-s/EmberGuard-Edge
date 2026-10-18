from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field
import random

from starlette.middleware.sessions import SessionMiddleware

from app.auth import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE,
    SESSION_SECRET,
    auth_error_message,
    credentials_configured,
    public_path,
    session_username,
    verify_credentials,
)

app = FastAPI(title="EmberGuard Edge")
BASE = Path(__file__).parent

app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")

simulation = {
    "scenario": "normal",
    "temperature": 28.0,
    "smoke": 120,
    "flame": False,
    "risk": 8,
    "state": "NORMAL",
    "reason": "No simulated hazard detected.",
    "updated": datetime.now().isoformat()
}


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


def calculate_risk(temp, smoke, flame):
    score = 0
    score += min(40, max(0, (temp - 25) * 0.8))
    score += min(35, max(0, (smoke - 100) / 20))
    if flame:
        score += 60
    return min(100, round(score))

def update_scenario(scenario):
    if scenario == "normal":
        temp = round(random.uniform(25, 32), 1)
        smoke = random.randint(80, 180)
        flame = False
    elif scenario == "smoke":
        temp = round(random.uniform(30, 42), 1)
        smoke = random.randint(450, 650)
        flame = False
    elif scenario == "heat":
        temp = round(random.uniform(65, 85), 1)
        smoke = random.randint(100, 250)
        flame = False
    elif scenario == "fire":
        temp = round(random.uniform(80, 110), 1)
        smoke = random.randint(750, 1000)
        flame = True
    else:
        return

    risk = calculate_risk(temp, smoke, flame)

    if flame or risk >= 80:
        state = "CRITICAL"
        reason = "Multiple simulated fire indicators detected."
    elif risk >= 35:
        state = "WARNING"
        reason = "Elevated simulated heat or smoke detected."
    else:
        state = "NORMAL"
        reason = "No simulated hazard detected."

    simulation.update({
        "scenario": scenario,
        "temperature": temp,
        "smoke": smoke,
        "flame": flame,
        "risk": risk,
        "state": state,
        "reason": reason,
        "updated": datetime.now().isoformat()
    })


@app.middleware("http")
async def require_authentication(request: Request, call_next):
    path = request.url.path

    if public_path(path) or path == "/api/logout":
        return await call_next(request)

    user = session_username(request.session)
    if user:
        return await call_next(request)

    # Unauthenticated: APIs get 401; browser pages redirect to login
    if path.startswith("/api/"):
        return JSONResponse({"error": "Unauthorized", "detail": "Login required."}, status_code=401)

    if path.startswith("/static/"):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    return RedirectResponse(url="/login", status_code=303)


# SessionMiddleware must be added last so it is outermost and request.session is available above.
# Hackathon prototype: use HTTPS and https_only=True before any public hosting.
_secret = SESSION_SECRET or "insecure-dev-only-change-me"
app.add_middleware(
    SessionMiddleware,
    secret_key=_secret,
    session_cookie=SESSION_COOKIE_NAME,
    max_age=SESSION_MAX_AGE,
    same_site="lax",
    https_only=False,
)


@app.get("/login")
def login_page(request: Request):
    if session_username(request.session):
        return RedirectResponse(url="/", status_code=303)
    return FileResponse(BASE / "static" / "login.html")


@app.post("/api/login")
async def login(payload: LoginRequest, request: Request):
    if not credentials_configured():
        return JSONResponse(
            {"error": "misconfigured", "detail": auth_error_message()},
            status_code=503,
        )

    if not verify_credentials(payload.username, payload.password):
        # Do not reveal which field failed; never echo password back.
        return JSONResponse(
            {"error": "invalid_credentials", "detail": auth_error_message()},
            status_code=401,
        )

    request.session.clear()
    request.session["user"] = payload.username.strip()
    return {"ok": True, "user": payload.username.strip()}


@app.post("/api/logout")
async def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@app.get("/")
def dashboard():
    return FileResponse(BASE / "static" / "index.html")

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "mode": "SIMULATION",
        "hardware_connected": False
    }

@app.get("/api/status")
def status():
    return simulation

@app.post("/api/scenario/{scenario}")
def set_scenario(scenario: str):
    if scenario not in ["normal", "smoke", "heat", "fire"]:
        return {"error": "Unknown scenario"}
    update_scenario(scenario)
    return simulation

@app.post("/api/simulate")
def simulate():
    update_scenario(simulation["scenario"])
    return simulation
