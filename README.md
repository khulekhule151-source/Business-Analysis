# Business Analysis V3 Professional

Full-stack business analytics system:
- FastAPI backend
- Render PostgreSQL
- Role-based OWNER / CLIENT access
- Professional Windows desktop dashboard
- Web login/dashboard
- CSV/Excel analysis
- KPI cards, charts, filters, automatic insights, data-quality analysis and exports

## Render
The included `render.yaml` pins the API to Python 3.13.5 and uses a deterministic pip build command. The API service lives in `Backend/`; the static website lives in `Website/`.

Render's current default Python for new native services is 3.14.3, so the explicit Python pin prevents dependency resolution from falling back to source builds for packages that do not have matching wheels.

Set these Blueprint values when prompted:
- `OWNER_EMAIL` — initial owner email
- `OWNER_PASSWORD` — strong initial owner password

Never commit secrets.
