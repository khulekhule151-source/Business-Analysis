from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, io, hmac, hashlib, secrets, time, json
from datetime import datetime, timezone
import pandas as pd

APP_NAME = "BUSINESS ANALYSIS Owner Control Center"
APP_VERSION = "2.0.0"
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "admin")
OWNER_PASSWORD = os.getenv("OWNER_PASSWORD", "")
OWNER_TOKEN_SECRET = os.getenv("OWNER_TOKEN_SECRET", "")
TELEMETRY_KEY = os.getenv("TELEMETRY_KEY", "")

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:
    psycopg = None

app = FastAPI(title=APP_NAME, version=APP_VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

class LoginRequest(BaseModel):
    username: str
    password: str

class TelemetryEvent(BaseModel):
    installation_id: str
    event_name: str
    app_version: str = APP_VERSION
    os_name: str = ""
    occurred_at: str = ""

def db_conn():
    url=os.getenv("DATABASE_URL")
    if not url or psycopg is None: return None
    return psycopg.connect(url, row_factory=dict_row)

def init_db():
    c=db_conn()
    if not c: return
    with c.cursor() as cur:
        cur.execute("""CREATE TABLE IF NOT EXISTS installations (installation_id TEXT PRIMARY KEY, first_seen TIMESTAMPTZ NOT NULL, last_seen TIMESTAMPTZ NOT NULL, app_version TEXT, os_name TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS telemetry_events (id BIGSERIAL PRIMARY KEY, installation_id TEXT NOT NULL, event_name TEXT NOT NULL, app_version TEXT, os_name TEXT, occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""")
    c.commit(); c.close()

@app.on_event("startup")
def startup(): init_db()

def make_token(username):
    if not OWNER_TOKEN_SECRET: return None
    payload=f"{username}|{int(time.time())+86400}"
    sig=hmac.new(OWNER_TOKEN_SECRET.encode(),payload.encode(),hashlib.sha256).hexdigest()
    return payload+"."+sig

def require_owner(authorization: str|None = Header(default=None)):
    if not OWNER_TOKEN_SECRET:
        raise HTTPException(503,"OWNER_TOKEN_SECRET is not configured on the server")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401,"Owner authentication required")
    token=authorization.split(" ",1)[1].strip()
    try: payload,sig=token.rsplit(".",1); username,expiry=payload.split("|",1)
    except ValueError: raise HTTPException(401,"Invalid owner token")
    expected=hmac.new(OWNER_TOKEN_SECRET.encode(),payload.encode(),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig,expected) or int(expiry)<int(time.time()) or username!=OWNER_USERNAME:
        raise HTTPException(401,"Invalid or expired owner token")
    return username

@app.get("/health")
def health():
    return {"status":"ok","service":APP_NAME,"version":APP_VERSION,"time":datetime.now(timezone.utc).isoformat()}

@app.post("/api/owner/login")
def owner_login(body: LoginRequest):
    if not OWNER_PASSWORD: raise HTTPException(503,"OWNER_PASSWORD is not configured on the server")
    if not hmac.compare_digest(body.username.strip(),OWNER_USERNAME) or not hmac.compare_digest(body.password,OWNER_PASSWORD):
        raise HTTPException(401,"Invalid owner credentials")
    token=make_token(OWNER_USERNAME)
    if not token: raise HTTPException(503,"OWNER_TOKEN_SECRET is not configured on the server")
    return {"success":True,"token":token,"username":OWNER_USERNAME,"expires_in":86400}

@app.get("/api/owner/summary")
def owner_summary(_: str=Depends(require_owner)):
    c=db_conn()
    if not c:
        return {"success":True,"database":"not configured","total_installations":0,"active_users":0,"last_seen":None,"events":0}
    with c.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM installations"); total=cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) AS n FROM installations WHERE last_seen >= NOW()-INTERVAL '30 days'"); active=cur.fetchone()["n"]
        cur.execute("SELECT MAX(last_seen) AS t FROM installations"); last=cur.fetchone()["t"]
        cur.execute("SELECT COUNT(*) AS n FROM telemetry_events"); events=cur.fetchone()["n"]
    c.close()
    return {"success":True,"total_installations":total,"active_users":active,"last_seen":last.isoformat() if last else None,"telemetry_events":events}

@app.post("/api/telemetry")
def telemetry(event: TelemetryEvent, x_telemetry_key: str|None=Header(default=None)):
    if TELEMETRY_KEY and not hmac.compare_digest(x_telemetry_key or "", TELEMETRY_KEY):
        raise HTTPException(401,"Invalid telemetry key")
    iid=event.installation_id.strip()
    if not iid: raise HTTPException(400,"installation_id is required")
    now=datetime.now(timezone.utc)
    c=db_conn()
    if c:
        with c.cursor() as cur:
            cur.execute("""INSERT INTO installations(installation_id,first_seen,last_seen,app_version,os_name) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(installation_id) DO UPDATE SET last_seen=EXCLUDED.last_seen, app_version=EXCLUDED.app_version, os_name=EXCLUDED.os_name""",(iid,now,now,event.app_version[:80],event.os_name[:80]))
            cur.execute("INSERT INTO telemetry_events(installation_id,event_name,app_version,os_name,occurred_at) VALUES(%s,%s,%s,%s,%s)",(iid,event.event_name[:80],event.app_version[:80],event.os_name[:80],now))
        c.commit(); c.close()
    return {"success":True}

def analyze_df(df):
    original_rows, original_columns=len(df),len(df.columns)
    df=df.copy(); df.columns=[str(c).strip().lower().replace(" ","_") for c in df.columns]
    aliases={"date":["date","transaction_date"],"product":["product","item","service","product_name"],"category":["category","type"],"sales":["sales","revenue","amount","price"],"cost":["cost","expense","expenses"],"quantity":["quantity","qty","units"],"customer":["customer","customer_name","client"]}
    rename={}
    for target,choices in aliases.items():
        for choice in choices:
            if choice in df.columns: rename[choice]=target; break
    df=df.rename(columns=rename)
    missing=[c for c in ("date","product","sales") if c not in df.columns]
    if missing: raise ValueError("Missing required columns: "+", ".join(missing))
    for col in ("category","customer"):
        if col not in df: df[col]="General" if col=="category" else "Walk-in"
    for col in ("cost","quantity"):
        if col not in df: df[col]=0 if col=="cost" else 1
    df["date"]=pd.to_datetime(df["date"],errors="coerce"); df["sales"]=pd.to_numeric(df["sales"],errors="coerce").fillna(0); df["cost"]=pd.to_numeric(df["cost"],errors="coerce").fillna(0); df["quantity"]=pd.to_numeric(df["quantity"],errors="coerce").fillna(1)
    missing_values=int(df.isna().sum().sum()); duplicate_rows=int(df.duplicated().sum()); df=df.dropna(subset=["date"]); df=df.drop_duplicates();
    for col,default in (("product","Unknown"),("category","General"),("customer","Walk-in")):
        df[col]=df[col].fillna(default).astype(str).str.strip().replace("",default)
    df["date"]=df["date"].dt.strftime("%Y-%m-%d")
    numeric=df.select_dtypes(include="number"); stats={}
    for c in numeric.columns: stats[c]={"total":float(numeric[c].sum()),"average":float(numeric[c].mean()),"min":float(numeric[c].min()),"max":float(numeric[c].max())}
    cats={}
    for c in ("product","category","customer"):
        if c in df: cats[c]=df[c].value_counts().head(10).to_dict()
    preview=json.loads(df.head(20).to_json(orient="records"))
    return {"success":True,"file":{"name":"uploaded"},"dataset":{"original_rows":original_rows,"original_columns":original_columns,"cleaned_rows":len(df),"cleaned_columns":len(df.columns)},"data_quality":{"missing_values":missing_values,"duplicate_rows":duplicate_rows},"numeric_summary":stats,"categorical_summary":cats,"preview":preview}

@app.post("/api/analyze")
async def analyze(file: UploadFile=File(...)):
    raw=await file.read(); name=(file.filename or "upload").lower()
    try:
        if name.endswith(".csv"): df=pd.read_csv(io.BytesIO(raw))
        elif name.endswith((".xlsx",".xls")): df=pd.read_excel(io.BytesIO(raw))
        else: raise ValueError("Only CSV and Excel files are supported")
        result=analyze_df(df); result["file"]= {"name":file.filename,"size_bytes":len(raw)}; return result
    except Exception as e: raise HTTPException(400,str(e))
