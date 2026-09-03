import os, json, math, webbrowser, traceback
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
import pandas as pd
import requests
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from api_client import APIClient

APP_NAME = "Business Analysis V3 Professional"
CONFIG_FILE = Path.home() / ".business_analysis_v3.json"
DEFAULT_API = os.getenv("BUSINESS_ANALYSIS_API_URL", "https://business-analysis-v3-api.onrender.com")
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME); self.geometry("1450x900"); self.minsize(1100,700)
        self.api_url = self.load_config().get("api_url", DEFAULT_API)
        self.api = APIClient(self.api_url)
        self.user = None; self.current_dataset=None; self.current_df=pd.DataFrame(); self.filtered_df=pd.DataFrame()
        self.colors={"bg":"#0b1220","panel":"#111827","panel2":"#172033","text":"#f8fafc","muted":"#94a3b8","accent":"#3b82f6","green":"#22c55e","red":"#ef4444","amber":"#f59e0b"}
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.show_login()

    def load_config(self):
        try: return json.loads(CONFIG_FILE.read_text())
        except Exception: return {}
    def save_config(self):
        try: CONFIG_FILE.write_text(json.dumps({"api_url":self.api_url}))
        except Exception: pass
    def clear(self):
        for w in self.winfo_children(): w.destroy()
    def fmt(self,v,prefix="R "):
        try: return prefix+f"{float(v):,.2f}"
        except Exception: return prefix+"0.00"
    def pct(self,v):
        try: return f"{float(v):.1f}%"
        except Exception: return "0.0%"
    def check_api_status(self):
        """Safe API health check; intentionally exists on App to prevent callback AttributeError."""
        label=getattr(self,"api_status_label",None)
        try:
            r=self.api.health(); online=r.ok
            text="● API ONLINE" if online else f"● API ERROR {r.status_code}"
            if label and label.winfo_exists(): label.configure(text=text, text_color=self.colors["green"] if online else self.colors["red"])
            return online
        except Exception:
            if label and label.winfo_exists(): label.configure(text="● API OFFLINE", text_color=self.colors["red"])
            return False
    def show_login(self):
        self.clear(); self.user=None; self.current_dataset=None; self.current_df=pd.DataFrame()
        outer=ctk.CTkFrame(self,fg_color=self.colors["bg"]); outer.pack(fill="both",expand=True)
        card=ctk.CTkFrame(outer,width=520,height=590,fg_color=self.colors["panel"],corner_radius=22); card.place(relx=.5,rely=.5,anchor="center"); card.pack_propagate(False)
        ctk.CTkLabel(card,text="BUSINESS ANALYSIS",font=ctk.CTkFont(size=30,weight="bold")).pack(pady=(55,2))
        ctk.CTkLabel(card,text="V3 PROFESSIONAL BI",font=ctk.CTkFont(size=16,weight="bold"),text_color=self.colors["accent"]).pack()
        ctk.CTkLabel(card,text="Secure analytics • dashboards • reports",text_color=self.colors["muted"]).pack(pady=(4,35))
        ctk.CTkLabel(card,text="API URL",anchor="w").pack(fill="x",padx=55)
        self.api_entry=ctk.CTkEntry(card,height=42); self.api_entry.pack(fill="x",padx=55,pady=(6,18)); self.api_entry.insert(0,self.api_url)
        ctk.CTkLabel(card,text="Email",anchor="w").pack(fill="x",padx=55)
        self.email=ctk.CTkEntry(card,height=42); self.email.pack(fill="x",padx=55,pady=(6,12))
        ctk.CTkLabel(card,text="Password",anchor="w").pack(fill="x",padx=55)
        self.password=ctk.CTkEntry(card,height=42,show="•"); self.password.pack(fill="x",padx=55,pady=(6,22))
        self.login_status=ctk.CTkLabel(card,text=""); self.login_status.pack(pady=2)
        ctk.CTkButton(card,text="SIGN IN",height=46,corner_radius=10,font=ctk.CTkFont(size=15,weight="bold"),command=self.login).pack(fill="x",padx=55,pady=12)
        self.api_status_label=ctk.CTkLabel(card,text="● Checking API...",text_color=self.colors["muted"]); self.api_status_label.pack(pady=8)
        ctk.CTkButton(card,text="Test API Connection",fg_color="transparent",border_width=1,command=self.manual_api_test).pack()
        self.after(150,self.check_api_status)

    def manual_api_test(self):
        self.api_url=self.api_entry.get().strip().rstrip('/'); self.api=APIClient(self.api_url); self.save_config(); self.check_api_status()
    def login(self):
        self.api_url=self.api_entry.get().strip().rstrip('/'); self.api=APIClient(self.api_url); self.save_config()
        try:
            data=self.api.login(self.email.get().strip(),self.password.get()); self.user=data["user"]; self.show_shell()
        except Exception as e: self.login_status.configure(text=f"Login failed: {self.error_text(e)}",text_color=self.colors["red"])
    def error_text(self,e):
        if isinstance(e,requests.HTTPError) and getattr(e,"response",None) is not None:
            try: return e.response.json().get("detail",str(e))
            except Exception: return str(e)
        return str(e)

    def show_shell(self):
        self.clear(); self.grid_columnconfigure(1,weight=1); self.grid_rowconfigure(0,weight=1)
        self.sidebar=ctk.CTkFrame(self,width=245,corner_radius=0,fg_color="#0f172a"); self.sidebar.grid(row=0,column=0,sticky="nsew"); self.sidebar.grid_propagate(False)
        ctk.CTkLabel(self.sidebar,text="BA V3",font=ctk.CTkFont(size=30,weight="bold")).pack(pady=(32,0))
        ctk.CTkLabel(self.sidebar,text="PROFESSIONAL BI",font=ctk.CTkFont(size=12,weight="bold"),text_color=self.colors["accent"]).pack(pady=(0,30))
        self.nav_buttons=[]
        items=[("Dashboard",self.show_dashboard),("Data Analysis",self.show_analysis),("Reports & Exports",self.show_reports)]
        if self.user["role"]=="OWNER": items.insert(0,("Owner Control Center",self.show_owner_center))
        for name,fn in items:
            b=ctk.CTkButton(self.sidebar,text=name,anchor="w",height=44,fg_color="transparent",hover_color=self.colors["panel2"],command=fn); b.pack(fill="x",padx=18,pady=4); self.nav_buttons.append(b)
        spacer=ctk.CTkFrame(self.sidebar,fg_color="transparent"); spacer.pack(fill="both",expand=True)
        ctk.CTkLabel(self.sidebar,text=self.user.get("name") or self.user.get("email"),wraplength=200,justify="left").pack(padx=18,pady=3,anchor="w")
        ctk.CTkLabel(self.sidebar,text=self.user["role"],text_color=self.colors["accent"]).pack(padx=18,pady=(0,15),anchor="w")
        ctk.CTkButton(self.sidebar,text="Logout",fg_color="#334155",command=self.show_login).pack(fill="x",padx=18,pady=(0,25))
        self.main=ctk.CTkFrame(self,fg_color=self.colors["bg"],corner_radius=0); self.main.grid(row=0,column=1,sticky="nsew"); self.main.grid_rowconfigure(1,weight=1); self.main.grid_columnconfigure(0,weight=1)
        self.header=ctk.CTkFrame(self.main,fg_color=self.colors["panel"],height=72,corner_radius=0); self.header.grid(row=0,column=0,sticky="ew"); self.header.grid_columnconfigure(0,weight=1)
        self.page_title=ctk.CTkLabel(self.header,text="Dashboard",font=ctk.CTkFont(size=24,weight="bold")); self.page_title.grid(row=0,column=0,padx=25,pady=18,sticky="w")
        self.api_status_label=ctk.CTkLabel(self.header,text="● API",text_color=self.colors["muted"]); self.api_status_label.grid(row=0,column=1,padx=25)
        self.content=ctk.CTkScrollableFrame(self.main,fg_color=self.colors["bg"]); self.content.grid(row=1,column=0,sticky="nsew",padx=0,pady=0); self.content.grid_columnconfigure(0,weight=1)
        self.after(100,self.check_api_status); self.show_dashboard()
    def set_title(self,t): self.page_title.configure(text=t)
    def clear_content(self,title=None):
        for w in self.content.winfo_children(): w.destroy()
        if title: self.set_title(title)
    def select_nav(self,name):
        for b in self.nav_buttons: b.configure(fg_color=self.colors["panel2"] if b.cget("text")==name else "transparent")

    def show_dashboard(self):
        self.select_nav("Dashboard"); self.clear_content("Dashboard")
        if self.user["role"]=="OWNER": return self.render_owner_dashboard()
        self.render_client_dashboard()
    def render_owner_dashboard(self):
        try: ov=self.api.get('/api/owner/overview'); clients=self.api.get('/api/owner/clients')
        except Exception as e: return self.show_error("Could not load owner dashboard",e)
        self.kpi_grid(ov,[("Total Clients","clients","#"),("Active Clients","active_clients","#"),("Total Users","users","#"),("Datasets","datasets","#"),("Revenue","revenue","R "),("Profit","profit","R ")])
        self.section("Business Portfolio")
        table=self.make_table(["Client","Status","Datasets","Revenue","Last Seen"])
        for c in clients: table.insert("","end",values=(c["name"],c["status"],c["datasets"],self.fmt(c["revenue"]),self.datefmt(c.get("last_seen"))))
        table.pack(fill="x",padx=5,pady=(0,20))
    def render_client_dashboard(self):
        try: data=self.api.get('/api/client/dashboard'); self.datasets=data.get("datasets",[]); totals=data.get("totals",{})
        except Exception as e: return self.show_error("Could not load dashboard",e)
        self.kpi_grid(totals,[("Revenue","revenue","R "),("Cost","cost","R "),("Profit","profit","R "),("Profit Margin","margin","%"),("Rows Analysed","rows","#"),("Datasets","datasets","#")])
        self.section("Latest Analysis")
        if not self.datasets:
            self.empty_state("No datasets yet","Upload a CSV or Excel file in Data Analysis to build your dashboard.",self.show_analysis); return
        cards=ctk.CTkFrame(self.content,fg_color="transparent"); cards.pack(fill="x",padx=5,pady=5)
        for d in self.datasets[:4]:
            card=ctk.CTkFrame(cards,fg_color=self.colors["panel"],corner_radius=12); card.pack(side="left",fill="both",expand=True,padx=5)
            ctk.CTkLabel(card,text=d["filename"],font=ctk.CTkFont(size=14,weight="bold"),wraplength=240).pack(padx=15,pady=(15,5))
            ctk.CTkLabel(card,text=f"Revenue {self.fmt(d['revenue'])}",text_color=self.colors["green"]).pack(padx=15,pady=2)
            ctk.CTkLabel(card,text=f"Profit {self.fmt(d['profit'])}").pack(padx=15,pady=2)
            ctk.CTkLabel(card,text=f"Quality {self.pct(d['quality'])}").pack(padx=15,pady=(2,15))
            ctk.CTkButton(card,text="Open Analysis",command=lambda x=d:self.open_dataset(x)).pack(padx=15,pady=(0,15))
    def kpi_grid(self,data,items):
        frame=ctk.CTkFrame(self.content,fg_color="transparent"); frame.pack(fill="x",padx=5,pady=12)
        for i in range(3): frame.grid_columnconfigure(i,weight=1)
        for i,(label,key,prefix) in enumerate(items):
            val=data.get(key,0); text=(prefix+f"{float(val):,.1f}" if prefix=="%" else (prefix+f"{float(val):,.2f}" if prefix=="R " else f"{int(val):,}"))
            card=ctk.CTkFrame(frame,fg_color=self.colors["panel"],corner_radius=12); card.grid(row=i//3,column=i%3,sticky="ew",padx=5,pady=5)
            ctk.CTkLabel(card,text=label,text_color=self.colors["muted"],font=ctk.CTkFont(size=12,weight="bold")).pack(anchor="w",padx=18,pady=(15,2))
            ctk.CTkLabel(card,text=text,font=ctk.CTkFont(size=24,weight="bold")).pack(anchor="w",padx=18,pady=(0,15))
    def section(self,title): ctk.CTkLabel(self.content,text=title,font=ctk.CTkFont(size=17,weight="bold")).pack(anchor="w",padx=10,pady=(15,8))
    def empty_state(self,title,desc,cmd=None):
        f=ctk.CTkFrame(self.content,fg_color=self.colors["panel"],corner_radius=15); f.pack(fill="x",padx=10,pady=20)
        ctk.CTkLabel(f,text=title,font=ctk.CTkFont(size=20,weight="bold")).pack(pady=(30,5)); ctk.CTkLabel(f,text=desc,text_color=self.colors["muted"]).pack(pady=5)
        if cmd: ctk.CTkButton(f,text="Get Started",command=cmd).pack(pady=(15,30))
    def show_error(self,title,e): messagebox.showerror(title,self.error_text(e))
    def datefmt(self,x):
        if not x:return "Never"
        return str(x)[:19].replace("T"," ")

    def show_analysis(self):
        self.select_nav("Data Analysis"); self.clear_content("Data Analysis")
        top=ctk.CTkFrame(self.content,fg_color=self.colors["panel"],corner_radius=12); top.pack(fill="x",padx=5,pady=10)
        ctk.CTkLabel(top,text="Professional Data Workspace",font=ctk.CTkFont(size=19,weight="bold")).pack(side="left",padx=18,pady=18)
        ctk.CTkButton(top,text="Upload CSV / Excel",command=self.upload_file).pack(side="right",padx=10,pady=12)
        if self.current_dataset:
            self.render_analysis()
        else:
            try: ds=self.api.get('/api/client/datasets') if self.user['role']=='CLIENT' else []
            except Exception: ds=[]
            if ds:
                self.section("Choose a dataset")
                for d in ds:
                    ctk.CTkButton(self.content,text=f"{d['filename']}  •  {d['rows']:,} rows  •  Quality {d['quality']:.1f}%",anchor="w",command=lambda x=d:self.open_dataset(x)).pack(fill="x",padx=10,pady=4)
            else: self.empty_state("No dataset selected","Upload a CSV or Excel file to activate KPI cards, filters, charts, insights and quality checks.",self.upload_file)
    def upload_file(self):
        path=filedialog.askopenfilename(filetypes=[("CSV files","*.csv"),("Excel files","*.xlsx *.xls")])
        if not path:return
        if self.user['role']!='CLIENT': messagebox.showinfo("Owner account","Use a client account to upload business datasets. The Owner Control Center manages clients and system activity."); return
        try:
            result=self.api.post_file('/api/client/datasets/analyze',path); self.open_dataset(result); messagebox.showinfo("Analysis complete","Dataset uploaded and analysed successfully.")
        except Exception as e: self.show_error("Upload failed",e)
    def open_dataset(self,d):
        try:
            detail=self.api.get(f"/api/client/datasets/{d['id']}")
            self.current_dataset=detail; self.current_df=pd.DataFrame(detail.get('data',[])); self.filtered_df=self.current_df.copy(); self.show_analysis()
        except Exception as e: self.show_error("Dataset error",e)
    def render_analysis(self):
        d=self.current_dataset; df=self.current_df.copy()
        self.kpi_grid(d.get("metrics",{}),[("Revenue","revenue","R "),("Cost","cost","R "),("Profit","profit","R "),("Profit Margin","margin","%"),("Orders / Rows","orders","#"),("Average Order","avg_order","R ")])
        self.render_filters(df)
        self.section("Visual Analytics")
        chartrow=ctk.CTkFrame(self.content,fg_color="transparent"); chartrow.pack(fill="both",expand=True,padx=5)
        chartrow.grid_columnconfigure((0,1),weight=1)
        self.plot_summary(chartrow,0,self.filtered_df,d)
        self.plot_category(chartrow,1,self.filtered_df,d)
        self.render_insights(d,self.filtered_df)
        self.render_quality(d)
        self.section("Filtered Data Preview")
        ctk.CTkLabel(self.content,text=f"Showing {len(self.filtered_df):,} of {len(df):,} rows",text_color=self.colors["muted"]).pack(anchor="w",padx=10)
        t=self.make_table(list(self.filtered_df.columns)[:8])
        for _,r in self.filtered_df.head(100).iterrows(): t.insert("","end",values=[str(r.get(c,""))[:50] for c in list(self.filtered_df.columns)[:8]])
        t.pack(fill="x",padx=10,pady=8)
    def render_filters(self,df):
        self.section("Advanced Filters")
        f=ctk.CTkFrame(self.content,fg_color=self.colors["panel"],corner_radius=12); f.pack(fill="x",padx=10,pady=5)
        f.grid_columnconfigure(1,weight=1)
        ctk.CTkLabel(f,text="Search all text").grid(row=0,column=0,padx=12,pady=12)
        self.search_var=tk.StringVar(); search=ctk.CTkEntry(f,textvariable=self.search_var,placeholder_text="customer, product, region..."); search.grid(row=0,column=1,sticky="ew",padx=12,pady=12)
        ctk.CTkLabel(f,text="Category").grid(row=1,column=0,padx=12,pady=12)
        cols=list(df.columns); self.cat_var=tk.StringVar(value=cols[0] if cols else ""); cat=ctk.CTkComboBox(f,values=cols or [""],variable=self.cat_var); cat.grid(row=1,column=1,sticky="ew",padx=12,pady=12)
        ctk.CTkLabel(f,text="Value").grid(row=2,column=0,padx=12,pady=12)
        self.val_var=tk.StringVar(); val=ctk.CTkEntry(f,textvariable=self.val_var,placeholder_text="exact/partial value"); val.grid(row=2,column=1,sticky="ew",padx=12,pady=12)
        ctk.CTkButton(f,text="Apply Filters",command=self.apply_filters).grid(row=0,column=2,rowspan=2,padx=12,pady=12)
        ctk.CTkButton(f,text="Reset",fg_color="#334155",command=self.reset_filters).grid(row=2,column=2,padx=12,pady=12)
        self.search_var.trace_add("write",lambda *_: None)
    def apply_filters(self):
        df=self.current_df.copy(); q=self.search_var.get().strip().lower()
        if q and not df.empty:
            mask=df.astype(str).apply(lambda col:col.str.lower().str.contains(q,na=False)).any(axis=1); df=df[mask]
        col=self.cat_var.get(); val=self.val_var.get().strip().lower()
        if col and col in df.columns and val: df=df[df[col].astype(str).str.lower().str.contains(val,na=False)]
        self.filtered_df=df; self.render_analysis()
    def reset_filters(self): self.current_df=self.current_df.copy(); self.filtered_df=self.current_df.copy(); self.show_analysis()
    def plot_summary(self,parent,col,df,d):
        card=ctk.CTkFrame(parent,fg_color=self.colors["panel"],corner_radius=12); card.grid(row=0,column=col,sticky="nsew",padx=5,pady=5)
        fig=Figure(figsize=(5.4,3.3),dpi=90); ax=fig.add_subplot(111)
        metrics=d.get("metrics",{}); rev=float(metrics.get("revenue",0)); cost=float(metrics.get("cost",0)); profit=float(metrics.get("profit",0))
        ax.bar(["Revenue","Cost","Profit"],[rev,cost,profit]); ax.set_title("Financial Performance"); ax.ticklabel_format(axis='y',style='plain'); fig.tight_layout()
        canvas=FigureCanvasTkAgg(fig,master=card); canvas.draw(); canvas.get_tk_widget().pack(fill="both",expand=True,padx=8,pady=8)
    def plot_category(self,parent,col,df,d):
        card=ctk.CTkFrame(parent,fg_color=self.colors["panel"],corner_radius=12); card.grid(row=0,column=col,sticky="nsew",padx=5,pady=5)
        fig=Figure(figsize=(5.4,3.3),dpi=90); ax=fig.add_subplot(111)
        if df.empty: ax.text(.5,.5,"No data after filters",ha="center",va="center")
        else:
            cat=next((c for c in df.columns if any(k in str(c).lower() for k in ['category','product','region','branch','department','customer'])),None)
            revcol=d.get('metrics',{}).get('rev_col')
            if cat and revcol:
                vals=pd.to_numeric(df[revcol].astype(str).str.replace(r'[^0-9.\-]','',regex=True),errors='coerce').fillna(0)
                tmp=pd.DataFrame({'cat':df[cat].astype(str),'v':vals}).groupby('cat')['v'].sum().sort_values(ascending=False).head(8)
                ax.barh(tmp.index[::-1],tmp.values[::-1]); ax.set_title(f"Revenue by {cat}")
            else: ax.text(.5,.5,"Add a category + revenue column\nfor a category chart",ha="center",va="center")
        fig.tight_layout(); canvas=FigureCanvasTkAgg(fig,master=card); canvas.draw(); canvas.get_tk_widget().pack(fill="both",expand=True,padx=8,pady=8)
    def render_insights(self,d,df):
        self.section("Automatic Insights")
        f=ctk.CTkFrame(self.content,fg_color=self.colors["panel"],corner_radius=12); f.pack(fill="x",padx=10,pady=5)
        m=d.get("metrics",{}); q=d.get("quality_info",{}); insights=[]
        margin=float(m.get('margin',0)); profit=float(m.get('profit',0)); rev=float(m.get('revenue',0)); score=float(q.get('score',d.get('quality',0)))
        insights.append(("Strong point",f"Revenue totals {self.fmt(rev)} across {int(m.get('orders',len(df))):,} analysed rows."))
        insights.append(("Profitability",f"Profit is {self.fmt(profit)} with a {margin:.1f}% margin."))
        if margin<10: insights.append(("Attention", "Profit margin is below 10%. Review pricing, direct costs and high-cost products."))
        elif margin>=30: insights.append(("Opportunity", "Margin is above 30%. Identify the products/regions driving profitability and scale them."))
        if score<80: insights.append(("Data quality", f"Quality is {score:.1f}%. Clean missing values and duplicate rows before important decisions."))
        else: insights.append(("Data quality", f"Quality is {score:.1f}%. The dataset is reasonably complete for analysis."))
        for title,text in insights:
            row=ctk.CTkFrame(f,fg_color=self.colors["panel2"],corner_radius=8); row.pack(fill="x",padx=10,pady=5)
            ctk.CTkLabel(row,text=title.upper(),width=115,anchor="w",font=ctk.CTkFont(weight="bold"),text_color=self.colors["accent"]).pack(side="left",padx=12,pady=10)
            ctk.CTkLabel(row,text=text,anchor="w",wraplength=900).pack(side="left",fill="x",expand=True,pady=10)
    def render_quality(self,d):
        self.section("Data Quality Panel")
        q=d.get("quality_info",{}); frame=ctk.CTkFrame(self.content,fg_color=self.colors["panel"],corner_radius=12); frame.pack(fill="x",padx=10,pady=5)
        score=float(q.get('score',d.get('quality',0))); ctk.CTkLabel(frame,text=f"{score:.1f}%",font=ctk.CTkFont(size=32,weight="bold"),text_color=self.colors["green"] if score>=80 else self.colors["amber"] if score>=60 else self.colors["red"]).pack(side="left",padx=25,pady=18)
        details=f"Completeness: {q.get('completeness',0):.1f}%    •    Missing cells: {q.get('missing_cells',0):,}    •    Duplicate rows: {q.get('duplicate_rows',0):,}    •    Columns: {q.get('columns',0)}    •    Rows: {q.get('rows',0):,}"
        ctk.CTkLabel(frame,text=details,text_color=self.colors["muted"]).pack(side="left",padx=10)

    def show_reports(self):
        self.select_nav("Reports & Exports"); self.clear_content("Reports & Exports")
        if not self.current_dataset: self.empty_state("No dataset selected","Open a dataset first, then export the filtered or full analysis.",self.show_analysis); return
        d=self.current_dataset
        self.kpi_grid(d.get("metrics",{}),[("Revenue","revenue","R "),("Cost","cost","R "),("Profit","profit","R "),("Margin","margin","%"),("Rows","orders","#"),("Quality","quality","%")])
        self.section("Export Center")
        f=ctk.CTkFrame(self.content,fg_color=self.colors["panel"],corner_radius=12); f.pack(fill="x",padx=10,pady=10)
        ctk.CTkButton(f,text="Export Filtered CSV",height=42,command=lambda:self.export_csv(False)).pack(side="left",padx=10,pady=18)
        ctk.CTkButton(f,text="Export Excel Workbook",height=42,command=self.export_excel).pack(side="left",padx=10,pady=18)
        ctk.CTkButton(f,text="Generate PDF Report",height=42,command=self.export_pdf).pack(side="left",padx=10,pady=18)
        ctk.CTkButton(f,text="Export Full CSV",height=42,fg_color="#334155",command=lambda:self.export_csv(True)).pack(side="left",padx=10,pady=18)
        self.section("Report Contents")
        for x in ["Executive KPI summary","Financial performance","Automatic business insights","Data-quality assessment","Filtered data preview"]: ctk.CTkLabel(self.content,text="✓  "+x).pack(anchor="w",padx=25,pady=4)
    def export_csv(self,full=False):
        df=self.current_df if full else self.filtered_df; path=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV','*.csv')],initialfile='business_analysis_export.csv')
        if path: df.to_csv(path,index=False); messagebox.showinfo("Export complete",path)
    def export_excel(self):
        path=filedialog.asksaveasfilename(defaultextension='.xlsx',filetypes=[('Excel','*.xlsx')],initialfile='business_analysis_report.xlsx')
        if not path:return
        with pd.ExcelWriter(path,engine='openpyxl') as w:
            self.current_df.to_excel(w,index=False,sheet_name='Data'); pd.DataFrame([self.current_dataset.get('metrics',{})]).to_excel(w,index=False,sheet_name='KPIs'); pd.DataFrame([self.current_dataset.get('quality_info',{})]).to_excel(w,index=False,sheet_name='Data Quality')
        messagebox.showinfo("Export complete",path)
    def export_pdf(self):
        path=filedialog.asksaveasfilename(defaultextension='.pdf',filetypes=[('PDF','*.pdf')],initialfile='business_analysis_report.pdf')
        if not path:return
        d=self.current_dataset; m=d.get('metrics',{}); q=d.get('quality_info',{})
        doc=SimpleDocTemplate(path,pagesize=landscape(A4),rightMargin=30,leftMargin=30,topMargin=30,bottomMargin=30); styles=getSampleStyleSheet(); story=[Paragraph('Business Analysis V3 — Professional Report',styles['Title']),Spacer(1,12),Paragraph(f"Dataset: {d.get('filename','')}",styles['Normal']),Spacer(1,10)]
        data=[["Revenue","Cost","Profit","Margin","Rows","Quality"],[self.fmt(m.get('revenue')),self.fmt(m.get('cost')),self.fmt(m.get('profit')),self.pct(m.get('margin')),f"{int(m.get('orders',0)):,}",self.pct(q.get('score',d.get('quality',0)))]]
        t=Table(data,colWidths=[120]*6); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#1f2937')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),.5,colors.grey),('ALIGN',(0,0),(-1,-1),'CENTER'),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)])); story.append(t); story.append(Spacer(1,15)); story.append(Paragraph('Automatic Insights',styles['Heading2']))
        margin=float(m.get('margin',0)); score=float(q.get('score',d.get('quality',0))); insights=[f"Revenue is {self.fmt(m.get('revenue'))} across {int(m.get('orders',0)):,} rows.",f"Profit is {self.fmt(m.get('profit'))} at a {margin:.1f}% margin.",f"Data quality score is {score:.1f}%; missing cells: {q.get('missing_cells',0):,}; duplicates: {q.get('duplicate_rows',0):,}."]
        for x in insights: story.append(Paragraph('• '+x,styles['BodyText']))
        doc.build(story); messagebox.showinfo("PDF generated",path)

    def show_owner_center(self):
        if self.user['role']!='OWNER': return
        self.select_nav("Owner Control Center"); self.clear_content("Owner Control Center")
        try: ov=self.api.get('/api/owner/overview'); clients=self.api.get('/api/owner/clients')
        except Exception as e: return self.show_error("Owner Center",e)
        self.kpi_grid(ov,[("Clients","clients","#"),("Active Clients","active_clients","#"),("Users","users","#"),("Active 7d","active_users_7d","#"),("Datasets","datasets","#"),("Revenue","revenue","R ")])
        self.section("Client Management")
        create=ctk.CTkFrame(self.content,fg_color=self.colors["panel"],corner_radius=12); create.pack(fill='x',padx=10,pady=5)
        entries=[]
        for label in ['Business / Client Name','Contact Name','Login Email','Temporary Password']:
            e=ctk.CTkEntry(create,placeholder_text=label,width=210,show='•' if 'Password' in label else None); e.pack(side='left',padx=6,pady=15); entries.append(e)
        ctk.CTkButton(create,text='Create Client',command=lambda:self.create_client(entries)).pack(side='left',padx=8)
        table=self.make_table(['ID','Client','Status','Users','Datasets','Revenue','Last Seen'])
        table.pack(fill='x',padx=10,pady=10)
        for c in clients:
            table.insert('', 'end', iid=str(c['id']), values=(c['id'],c['name'],c['status'],c['users'],c['datasets'],self.fmt(c['revenue']),self.datefmt(c.get('last_seen'))))
        ctk.CTkButton(self.content,text='Suspend / Activate Selected Client',command=lambda:self.toggle_selected_client(table)).pack(anchor='e',padx=10,pady=5)
        self.section("Owner Responsibilities")
        ctk.CTkLabel(self.content,text="Owner accounts can manage clients and monitor system activity. Client accounts are restricted by the API to their own datasets.",text_color=self.colors['muted'],wraplength=1000).pack(anchor='w',padx=15,pady=5)
    def create_client(self,entries):
        vals=[e.get().strip() for e in entries]
        if not all(vals): return messagebox.showwarning('Missing information','Complete all client fields.')
        try:
            self.api.post_json('/api/owner/clients',{'name':vals[0],'contact_name':vals[1],'email':vals[2],'password':vals[3]}); messagebox.showinfo('Client created','Client login created successfully.'); self.show_owner_center()
        except Exception as e:self.show_error('Could not create client',e)
    def toggle_selected_client(self,table):
        sel=table.selection()
        if not sel:return messagebox.showwarning('Select client','Select a client first.')
        row=table.item(sel[0])['values']; new='suspended' if str(row[2])=='active' else 'active'
        try:self.api.patch_json(f"/api/owner/clients/{int(row[0])}/status",{'status':new}); self.show_owner_center()
        except Exception as e:self.show_error('Could not update client',e)
    def make_table(self,columns):
        wrap=ctk.CTkFrame(self.content,fg_color=self.colors['panel'],corner_radius=10); wrap.pack(fill='x',padx=10,pady=5)
        tree=ttk.Treeview(wrap,columns=columns,show='headings',height=8)
        for c in columns: tree.heading(c,text=c); tree.column(c,width=max(100,900//max(1,len(columns))),anchor='w')
        sy=ttk.Scrollbar(wrap,orient='vertical',command=tree.yview); tree.configure(yscrollcommand=sy.set); tree.pack(side='left',fill='x',expand=True,padx=5,pady=5); sy.pack(side='right',fill='y',pady=5)
        return tree

if __name__=='__main__':
    try: App().mainloop()
    except Exception:
        traceback.print_exc(); raise
