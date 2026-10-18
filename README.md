# 🔥 EmberGuard Edge

### Intelligent Fire Monitoring & Risk Analysis

**Detect early. Assess intelligently. Respond faster.**

EmberGuard Edge is a hackathon prototype demonstrating an offline-first fire monitoring dashboard. It simulates temperature, smoke, and flame sensor readings to show how changing environmental conditions can affect a fire-risk assessment.

## ✨ Features

- 📊 Fire monitoring dashboard
- 🌡️ Simulated temperature and smoke readings
- 🔥 Flame-trigger simulation
- 🛡️ Risk score and system status
- 📈 Risk monitoring chart
- 🧾 Event timeline and system diagnostics
- 🔐 Login authentication
- 🖥️ Local web application

## 🧰 Technology Stack

- Python
- FastAPI
- HTML, CSS and JavaScript
- Uvicorn

## 🚀 Run Locally

Clone the repository:

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd EmberGuard-Edge
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Start the application using the configured port and entry point. For the current local setup:

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Open `http://127.0.0.1:8001/login` in your browser.

Configure demo credentials in your local `.env` file. Never commit passwords or secret keys.

## 🧪 Demo Scenarios

- Normal environment
- Smoke detected
- High temperature
- Fire emergency

All sensor values and scenarios are simulated for demonstration.

## ⚠️ Disclaimer

EmberGuard Edge is a hackathon prototype, not a certified fire alarm or life-safety system. It has not been validated for real-world fire detection.

## 📌 Project Status

Prototype — local simulation and demonstration.

## 👨‍💻 Author

Add your name and team details here.
