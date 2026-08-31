# BUSINESS ANALYSIS — Backend + Owner Control Center
Publisher: KHÙLÈ KHÙLÈ III

Prepared for Render Web Service + Render Postgres.

## Local
py -m pip install -r requirements.txt
set BUSINESS_ANALYSIS_OWNER_USERNAME=owner
set BUSINESS_ANALYSIS_OWNER_PASSWORD=change-me
set BUSINESS_ANALYSIS_TELEMETRY_KEY=local-key
set BUSINESS_ANALYSIS_TOKEN_SECRET=local-secret
py -m uvicorn main:app --host 127.0.0.1 --port 8000

Open http://127.0.0.1:8000/

## Production
Push this backend to GitHub, then deploy the included render.yaml as a Render Blueprint. Set the four secret variables in Render. Render supplies the DATABASE_URL from its Postgres database. After deployment, use the generated HTTPS onrender.com URL, then add your own custom domain in Render and configure DNS at the domain registrar. Render provisions and renews TLS certificates and redirects HTTP to HTTPS.
