# EmberGuard Edge

Hackathon simulation prototype for intelligent fire monitoring. Sensor readings and risk scores are **simulated** and must not be used for real-life safety decisions.

## Quick start

```bash
cd emberguard-edge
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
copy .env.example .env
# Edit .env and set DEMO_USERNAME, DEMO_PASSWORD, and SESSION_SECRET

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) — you will be redirected to the login page.

## Authentication (hackathon prototype)

This project uses a **simple signed-session login** suitable for a local demo. It is **not enterprise-grade security**. Before any public hosting you should use HTTPS, rotate secrets, tighten cookie flags (`Secure` / `https_only`), and replace demo credentials with a real identity system.

### Configure credentials

1. Copy `.env.example` to `.env` (never commit `.env`).
2. Set:
   - `DEMO_USERNAME` — login username
   - `DEMO_PASSWORD` — login password
   - `SESSION_SECRET` — long random string used to sign session cookies  
     Example: `python -c "import secrets; print(secrets.token_hex(32))"`
   - `SESSION_MAX_AGE_SECONDS` — optional session lifetime (default `28800` = 8 hours)

### Log in

1. Start the app with Uvicorn (see above).
2. Visit `http://127.0.0.1:8000` — unauthenticated users are sent to `/login`.
3. Enter the username and password from your `.env`.
4. After a successful login you reach the existing Fire Intelligence Center dashboard.

Invalid credentials show an error on the login page and do not create a session. Protected pages and APIs (`/`, `/api/status`, `/api/scenario/...`, `/api/simulate`, etc.) return a redirect or `401` until you sign in.

### Log out

Use the **Logout** button in the dashboard header. The session cookie is cleared and you return to `/login`. Protected routes and APIs stay blocked until you sign in again. If a session expires, dashboard API calls redirect you to the login page.

### Security notes (demo only)

- Passwords and `SESSION_SECRET` must stay in `.env` only — they are never returned in API responses.
- Sessions are signed cookies with expiration (`SESSION_MAX_AGE_SECONDS`), `HttpOnly`, and `SameSite=Lax`.
- Local demo uses HTTP (`https_only=False`). Enable HTTPS and secure cookies before exposing the app on a network.
