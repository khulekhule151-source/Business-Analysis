import os, io, json, math, statistics
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Text, ForeignKey, func
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from jose import jwt, JWTError
import bcrypt

APP_VERSION = "3.0.0-professional"
SECRET_KEY = os.getenv("JWT_SECRET", "CHANGE-ME-IN-RENDER")
ALGORITHM = "HS256"
TOKEN_MINUTES = int(os.getenv("TOKEN_MINUTES", "1440"))
OWNER_EMAIL = os.getenv("OWNER_EMAIL", "owner@example.com").lower()
OWNER_PASSWORD = os.getenv("OWNER_PASSWORD", "ChangeMe123!")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./business_analysis_v3.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()
bearer = HTTPBearer(auto_error=False)

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True)
    name = Column(String(180), nullable=False)
    status = Column(String(30), default="active")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    users = relationship("User", back_populates="client")
    datasets = relationship("Dataset", back_populates="client")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="CLIENT")
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    name = Column(String(180), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen = Column(DateTime, nullable=True)
    client = relationship("Client", back_populates="users")

class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    rows = Column(Integer, default=0)
    columns = Column(Integer, default=0)
    revenue = Column(Float, default=0)
    cost = Column(Float, default=0)
    profit = Column(Float, default=0)
    quality = Column(Float, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    columns_json = Column(Text, default="[]")
    data_json = Column(Text, default="[]")
    quality_json = Column(Text, default="{}")
    metrics_json = Column(Text, default="{}")
    client = relationship("Client", back_populates="datasets")

Base.metadata.create_all(engine)

def db():
    s = SessionLocal()
    try: yield s
    finally: s.close()

def hash_password(p):
    return bcrypt.hashpw(p.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(p, h):
    try:
        return bcrypt.checkpw(p.encode("utf-8"), h.encode("utf-8"))
    except (ValueError, TypeError):
        return False
def token_for(user):
    exp = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MINUTES)
    return jwt.encode({"sub": str(user.id), "role": user.role, "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)

def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer), session: Session = Depends(db)):
    if not creds: raise HTTPException(401, "Authentication required")
    try: payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM]); uid = int(payload["sub"])
    except Exception: raise HTTPException(401, "Invalid or expired token")
    user = session.get(User, uid)
    if not user: raise HTTPException(401, "User not found")
    user.last_seen = datetime.now(timezone.utc); session.commit()
    return user

def owner_only(user=Depends(current_user)):
    if user.role != "OWNER": raise HTTPException(403, "Owner access required")
    return user

def client_only(user=Depends(current_user)):
    if user.role != "CLIENT": raise HTTPException(403, "Client access required")
    if not user.client_id: raise HTTPException(403, "Client account is not assigned")
    return user

def safe_json(x):
    return json.dumps(x, default=str, ensure_ascii=False)

def find_col(df, terms):
    for c in df.columns:
        n = str(c).strip().lower().replace(" ", "_")
        if any(t in n for t in terms): return c
    return None

def numeric_series(df, col):
    if not col: return pd.Series([0.0] * len(df), index=df.index)
    return pd.to_numeric(df[col].astype(str).str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce").fillna(0)

def analyze_df(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    rev_col = find_col(df, ["revenue","sales","amount","income","total","price"])
    cost_col = find_col(df, ["cost","expense","cogs","spend"])
    qty_col = find_col(df, ["quantity","qty","units"])
    date_col = find_col(df, ["date","time","day","month","created"])
    rev = numeric_series(df, rev_col)
    cost = numeric_series(df, cost_col)
    qty = numeric_series(df, qty_col)
    profit = rev - cost if cost_col else rev
    missing = int(df.isna().sum().sum())
    duplicates = int(df.duplicated().sum())
    total_cells = max(1, df.shape[0] * df.shape[1])
    completeness = max(0, min(100, (1 - missing / total_cells) * 100))
    unique_rows = df.drop_duplicates().shape[0]
    duplicate_score = max(0, 100 - (duplicates / max(1, len(df))) * 100)
    quality = round((completeness * .7) + (duplicate_score * .3), 1)
    data = df.head(20000).where(pd.notnull(df), None).to_dict(orient="records")
    metrics = {
        "revenue": round(float(rev.sum()), 2), "cost": round(float(cost.sum()), 2),
        "profit": round(float(profit.sum()), 2), "margin": round(float((profit.sum()/rev.sum()*100) if rev.sum() else 0), 2),
        "orders": int(len(df)), "units": round(float(qty.sum()), 2),
        "avg_order": round(float(rev.sum()/len(df)) if len(df) else 0, 2),
        "rev_col": str(rev_col) if rev_col else None, "cost_col": str(cost_col) if cost_col else None,
        "date_col": str(date_col) if date_col else None,
    }
    quality_info = {"score": quality, "missing_cells": missing, "duplicate_rows": duplicates,
                    "completeness": round(completeness,1), "columns": len(df.columns), "rows": len(df)}
    return metrics, quality_info, data, list(df.columns)

def seed_owner():
    s=SessionLocal()
    try:
        u=s.query(User).filter(func.lower(User.email)==OWNER_EMAIL).first()
        if not u:
            s.add(User(email=OWNER_EMAIL,password_hash=hash_password(OWNER_PASSWORD),role="OWNER",name="System Owner")); s.commit()
    finally: s.close()
seed_owner()

app = FastAPI(title="Business Analysis V3 API", version=APP_VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def root(): return {"name":"Business Analysis V3 API","version":APP_VERSION,"docs":"/docs"}
@app.get("/health")
def health(): return {"status":"ok","version":APP_VERSION,"time":datetime.now(timezone.utc).isoformat()}

class Login(BaseModel): email: EmailStr; password: str
class ClientCreate(BaseModel): name: str; email: EmailStr; password: str; contact_name: str = ""
class StatusUpdate(BaseModel): status: str

@app.post("/api/auth/login")
def login(body: Login, s: Session=Depends(db)):
    u=s.query(User).filter(func.lower(User.email)==body.email.lower()).first()
    if not u or not verify_password(body.password,u.password_hash): raise HTTPException(401,"Invalid email or password")
    u.last_seen=datetime.now(timezone.utc); s.commit()
    return {"access_token":token_for(u),"token_type":"bearer","user":{"id":u.id,"email":u.email,"role":u.role,"name":u.name,"client_id":u.client_id}}

@app.get("/api/auth/me")
def me(u=Depends(current_user)):
    return {"id":u.id,"email":u.email,"role":u.role,"name":u.name,"client_id":u.client_id}

@app.get("/api/owner/overview")
def owner_overview(u=Depends(owner_only), s:Session=Depends(db)):
    clients=s.query(Client).count(); active=s.query(Client).filter(Client.status=="active").count(); datasets=s.query(Dataset).count()
    revenue=s.query(func.coalesce(func.sum(Dataset.revenue),0)).scalar() or 0; profit=s.query(func.coalesce(func.sum(Dataset.profit),0)).scalar() or 0
    users=s.query(User).count(); now=datetime.now(timezone.utc); active_users=s.query(User).filter(User.last_seen!=None, User.last_seen>=now-timedelta(days=7)).count()
    return {"clients":clients,"active_clients":active,"datasets":datasets,"revenue":round(revenue,2),"profit":round(profit,2),"users":users,"active_users_7d":active_users}

@app.get("/api/owner/clients")
def owner_clients(u=Depends(owner_only), s:Session=Depends(db)):
    out=[]
    for c in s.query(Client).order_by(Client.created_at.desc()).all():
        ds=s.query(Dataset).filter(Dataset.client_id==c.id).all(); users=s.query(User).filter(User.client_id==c.id).all()
        out.append({"id":c.id,"name":c.name,"status":c.status,"created_at":c.created_at,"datasets":len(ds),"users":len(users),"revenue":round(sum(x.revenue or 0 for x in ds),2),"last_seen":max((x.last_seen for x in users if x.last_seen), default=None)})
    return out

@app.post("/api/owner/clients")
def create_client(body:ClientCreate,u=Depends(owner_only),s:Session=Depends(db)):
    if s.query(User).filter(func.lower(User.email)==body.email.lower()).first(): raise HTTPException(409,"Email already exists")
    c=Client(name=body.name.strip(),status="active"); s.add(c); s.flush()
    s.add(User(email=body.email.lower(),password_hash=hash_password(body.password),role="CLIENT",client_id=c.id,name=body.contact_name or body.name)); s.commit()
    return {"id":c.id,"message":"Client created"}

@app.patch("/api/owner/clients/{cid}/status")
def client_status(cid:int,body:StatusUpdate,u=Depends(owner_only),s:Session=Depends(db)):
    c=s.get(Client,cid)
    if not c: raise HTTPException(404,"Client not found")
    c.status=body.status if body.status in ["active","suspended"] else "active"; s.commit(); return {"message":"updated","status":c.status}

@app.get("/api/client/dashboard")
def client_dashboard(u=Depends(client_only),s:Session=Depends(db)):
    ds=s.query(Dataset).filter(Dataset.client_id==u.client_id).order_by(Dataset.created_at.desc()).all()
    return {"client":{"id":u.client_id,"name":u.client.name if u.client else ""},"datasets":[dataset_summary(d) for d in ds],"totals":aggregate_dataset_summaries(ds)}

def dataset_summary(d):
    return {"id":d.id,"filename":d.filename,"rows":d.rows,"columns":d.columns,"revenue":d.revenue,"cost":d.cost,"profit":d.profit,"quality":d.quality,"created_at":d.created_at,"metrics":json.loads(d.metrics_json or "{}"),"quality_info":json.loads(d.quality_json or "{}"),"columns_list":json.loads(d.columns_json or "[]")}
def aggregate_dataset_summaries(ds):
    revenue=sum(d.revenue or 0 for d in ds); cost=sum(d.cost or 0 for d in ds); profit=sum(d.profit or 0 for d in ds)
    return {"datasets":len(ds),"revenue":round(revenue,2),"cost":round(cost,2),"profit":round(profit,2),"margin":round(profit/revenue*100,2) if revenue else 0,"rows":sum(d.rows or 0 for d in ds)}

@app.post("/api/client/datasets/analyze")
def upload_dataset(file:UploadFile=File(...),u=Depends(client_only),s:Session=Depends(db)):
    raw=file.file.read()
    if len(raw)>100*1024*1024: raise HTTPException(413,"File exceeds 100 MB limit")
    try:
        if file.filename.lower().endswith(('.xlsx','.xls')): df=pd.read_excel(io.BytesIO(raw))
        elif file.filename.lower().endswith('.csv'): df=pd.read_csv(io.BytesIO(raw))
        else: raise HTTPException(400,"Only CSV and Excel files are supported")
    except HTTPException: raise
    except Exception as e: raise HTTPException(400,f"Could not read file: {e}")
    if df.empty: raise HTTPException(400,"The file contains no rows")
    metrics,qinfo,data,cols=analyze_df(df)
    d=Dataset(client_id=u.client_id,filename=file.filename,rows=len(df),columns=len(df.columns),revenue=metrics['revenue'],cost=metrics['cost'],profit=metrics['profit'],quality=qinfo['score'],columns_json=safe_json(cols),data_json=safe_json(data),quality_json=safe_json(qinfo),metrics_json=safe_json(metrics))
    s.add(d); s.commit(); s.refresh(d)
    return dataset_summary(d)

@app.get("/api/client/datasets")
def client_datasets(u=Depends(client_only),s:Session=Depends(db)):
    return [dataset_summary(d) for d in s.query(Dataset).filter(Dataset.client_id==u.client_id).order_by(Dataset.created_at.desc()).all()]

@app.get("/api/client/datasets/{did}")
def dataset_detail(did:int,u=Depends(client_only),s:Session=Depends(db)):
    d=s.get(Dataset,did)
    if not d or d.client_id!=u.client_id: raise HTTPException(404,"Dataset not found")
    return {**dataset_summary(d),"data":json.loads(d.data_json or "[]")}

@app.delete("/api/client/datasets/{did}")
def dataset_delete(did:int,u=Depends(client_only),s:Session=Depends(db)):
    d=s.get(Dataset,did)
    if not d or d.client_id!=u.client_id: raise HTTPException(404,"Dataset not found")
    s.delete(d); s.commit(); return {"message":"Dataset deleted"}
