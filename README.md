# Business Analysis V3 Professional

Full-stack business intelligence system:

- **Backend:** FastAPI + PostgreSQL + JWT/RBAC
- **Desktop:** CustomTkinter professional BI dashboard
- **Website:** secure login + owner/client workspace
- **Deployment:** Render via `render.yaml`

## Professional dashboard features

- KPI cards: revenue, cost, profit, margin, rows/orders, average order, datasets
- Advanced text/category filtering
- Financial performance chart
- Category revenue chart
- Automatic business insights
- Data-quality score, completeness, missing cells and duplicates
- CSV, Excel and PDF exports
- Polished Owner Control Center
- Client management and client status controls
- Backend-enforced client data isolation

## First run

1. Deploy the repository to Render using `render.yaml`.
2. Set `OWNER_EMAIL` and `OWNER_PASSWORD` in Render.
3. Verify `https://YOUR-API/health`.
4. On Windows install Desktop_App requirements:
   `pip install -r requirements.txt`
5. Start:
   `python business_analysis_v3.py`
6. Sign in with the owner account, create a client, then use the client login for dataset analysis.

The desktop app connects to Render; it does not run on Render.
