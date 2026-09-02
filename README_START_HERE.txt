BUSINESS ANALYSIS v2.0.0 — FULL STACK

Folders:
1. Backend — FastAPI service for Render + PostgreSQL.
2. Desktop_App — Windows desktop application with administrator login, Owner Control Center, dashboard, cleaning, reports and Render API connection.
3. Website — browser Owner Control Center.

IMPORTANT: The desktop application does NOT get uploaded to Render. Render hosts the Backend. The Website can be deployed as a separate Render Static Site. The desktop connects automatically to the Render API URL.

DEPLOY BACKEND:
- In Render, create/modify the Web Service from the Backend folder.
- Build: pip install -r requirements.txt
- Start: uvicorn main:app --host 0.0.0.0 --port $PORT
- Add DATABASE_URL, OWNER_USERNAME, OWNER_PASSWORD, OWNER_TOKEN_SECRET and optional TELEMETRY_KEY as environment variables.
- Keep the same PostgreSQL database if you are upgrading the existing service. Back it up first.

DESKTOP:
- Extract Desktop_App on Windows.
- Run install_requirements.bat, then run_business_analysis.bat.
- First launch creates the local administrator account.

WEBSITE:
- Deploy Website as a Render Static Site, or open index.html locally for testing.

DO NOT delete your existing Render service/database until the new backend has passed /health, /docs, /api/owner/login and /api/analyze tests.
