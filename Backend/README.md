# BUSINESS ANALYSIS — Backend + Owner Control Center

Render-ready FastAPI backend.

## Render settings
- Root Directory: `Backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health Check: `/health`

Set these environment variables in the Render service:
- `BUSINESS_ANALYSIS_OWNER_USERNAME`
- `BUSINESS_ANALYSIS_OWNER_PASSWORD`
- `BUSINESS_ANALYSIS_TELEMETRY_KEY`
- `BUSINESS_ANALYSIS_TOKEN_SECRET`
- `DATABASE_URL` — use the Render Postgres **Internal Database URL** when the database is attached to the service.

Never commit real credentials to GitHub.
