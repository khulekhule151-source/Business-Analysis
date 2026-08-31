import os, sqlite3, uuid, platform, json, urllib.request
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import hashlib, secrets

APP_NAME = "BUSINESS ANALYSIS"
PUBLISHER = "KHÙLÈ KHÙLÈ III"
APP_VERSION = "1.0.0"
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
try:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f: APP_CONFIG=json.load(f)
except Exception: APP_CONFIG={}
API_URL = os.getenv("BUSINESS_ANALYSIS_API_URL", APP_CONFIG.get("api_url", "https://YOUR-API-DOMAIN.example"))
TELEMETRY_KEY = os.getenv("BUSINESS_ANALYSIS_TELEMETRY_KEY", APP_CONFIG.get("telemetry_key", ""))

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "business_analysis.db")

def hash_value(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def init_db():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL, recovery_hash TEXT NOT NULL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT NOT NULL)""")
    con.commit()
    con.close()

def get_setting(key):
    con = sqlite3.connect(DB); cur = con.cursor()
    cur.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cur.fetchone(); con.close()
    return row[0] if row else None

def set_setting(key, value):
    con = sqlite3.connect(DB); cur = con.cursor()
    cur.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",(key,value))
    con.commit(); con.close()

def send_event(event):
    # Controlled telemetry: only event/app/device metadata. No business records.
    if not TELEMETRY_KEY or API_URL.startswith("https://YOUR-"):
        return
    install_id = get_setting("installation_id")
    payload = json.dumps({
        "installation_id": install_id, "app_version": APP_VERSION,
        "event": event, "os": platform.system()+" "+platform.release()
    }).encode()
    try:
        req=urllib.request.Request(API_URL.rstrip("/")+"/telemetry",
            data=payload, headers={"Content-Type":"application/json",
            "X-Telemetry-Key":TELEMETRY_KEY}, method="POST")
        urllib.request.urlopen(req, timeout=3).read()
    except Exception:
        pass

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} — {PUBLISHER}")
        self.geometry("1000x650")
        self.minsize(850,560)
        self.configure(bg="#0b1020")
        init_db()
        if not get_setting("installation_id"):
            set_setting("installation_id", str(uuid.uuid4()))
        self.user=None
        self.show_auth()

    def clear(self):
        for w in self.winfo_children(): w.destroy()

    def show_auth(self):
        self.clear()
        con=sqlite3.connect(DB); exists=con.execute("SELECT 1 FROM admin LIMIT 1").fetchone(); con.close()
        if not exists: self.setup()
        else: self.login()

    def panel(self):
        f=tk.Frame(self,bg="#121a2d",padx=38,pady=30)
        f.place(relx=.5,rely=.5,anchor="center",width=560,height=500)
        return f

    def setup(self):
        f=self.panel()
        tk.Label(f,text=APP_NAME,bg="#121a2d",fg="#55dfc3",font=("Segoe UI",22,"bold")).pack(pady=(0,2))
        tk.Label(f,text="Secure First-Time Setup",bg="#121a2d",fg="white",font=("Segoe UI",16,"bold")).pack(pady=(0,18))
        entries=[]
        for label in ["Administrator username","Password","Confirm password","Recovery code"]:
            tk.Label(f,text=label,bg="#121a2d",fg="#b9c4d9",anchor="w").pack(fill="x")
            e=tk.Entry(f,show="*" if "password" in label.lower() or "code" in label.lower() else "",font=("Segoe UI",12))
            e.pack(fill="x",pady=(3,10)); entries.append(e)
        def create():
            u,p,c,r=[e.get().strip() for e in entries]
            if not u or len(p)<8 or p!=c or len(r)<8:
                messagebox.showerror("Setup","Use a username, an 8+ character password, matching confirmation and an 8+ character recovery code."); return
            con=sqlite3.connect(DB)
            try:
                con.execute("INSERT INTO admin(username,password_hash,recovery_hash) VALUES(?,?,?)",(u,hash_value(p),hash_value(r)))
                con.commit()
            except sqlite3.IntegrityError:
                messagebox.showerror("Setup","Administrator already exists.")
                return
            finally: con.close()
            messagebox.showinfo("Setup","Administrator created. Save your recovery code safely.")
            self.login()
        tk.Button(f,text="CREATE ADMINISTRATOR",command=create,bg="#55dfc3",fg="#061016",font=("Segoe UI",11,"bold"),relief="flat",pady=10).pack(fill="x",pady=12)

    def login(self):
        f=self.panel()
        tk.Label(f,text=APP_NAME,bg="#121a2d",fg="#55dfc3",font=("Segoe UI",22,"bold")).pack(pady=(10,2))
        tk.Label(f,text="Administrator Login",bg="#121a2d",fg="white",font=("Segoe UI",16,"bold")).pack(pady=(0,25))
        tk.Label(f,text="Username",bg="#121a2d",fg="#b9c4d9").pack(anchor="w")
        u=tk.Entry(f,font=("Segoe UI",12)); u.pack(fill="x",pady=(3,12))
        tk.Label(f,text="Password",bg="#121a2d",fg="#b9c4d9").pack(anchor="w")
        p=tk.Entry(f,show="*",font=("Segoe UI",12)); p.pack(fill="x",pady=(3,12))
        def go():
            con=sqlite3.connect(DB); row=con.execute("SELECT username,password_hash FROM admin WHERE username=?",(u.get().strip(),)).fetchone(); con.close()
            if row and secrets.compare_digest(row[1],hash_value(p.get())):
                self.user=row[0]; send_event("login_success"); self.dashboard()
            else: messagebox.showerror("Login","Invalid username or password.")
        tk.Button(f,text="LOGIN",command=go,bg="#55dfc3",fg="#061016",font=("Segoe UI",11,"bold"),relief="flat",pady=10).pack(fill="x",pady=8)
        tk.Button(f,text="Forgot password / Recovery Code",command=self.recovery,bg="#121a2d",fg="#55dfc3",relief="flat").pack()

    def recovery(self):
        win=tk.Toplevel(self); win.title("Recovery"); win.geometry("430x300"); win.configure(bg="#121a2d")
        fields=[]
        for label in ["Username","Recovery code","New password"]:
            tk.Label(win,text=label,bg="#121a2d",fg="white").pack(anchor="w",padx=30,pady=(15,2))
            e=tk.Entry(win,show="*" if "code" in label.lower() or "password" in label.lower() else ""); e.pack(fill="x",padx=30); fields.append(e)
        def reset():
            u,r,p=[x.get().strip() for x in fields]
            con=sqlite3.connect(DB); row=con.execute("SELECT recovery_hash FROM admin WHERE username=?",(u,)).fetchone()
            if row and secrets.compare_digest(row[0],hash_value(r)) and len(p)>=8:
                con.execute("UPDATE admin SET password_hash=? WHERE username=?",(hash_value(p),u)); con.commit(); con.close(); win.destroy(); messagebox.showinfo("Recovery","Password reset. You can log in.")
            else: con.close(); messagebox.showerror("Recovery","Invalid recovery code or password.")
        tk.Button(win,text="RESET PASSWORD",command=reset,bg="#55dfc3",fg="#061016",relief="flat").pack(pady=20)

    def dashboard(self):
        self.clear(); send_event("dashboard_opened")
        top=tk.Frame(self,bg="#10182b",height=70); top.pack(fill="x")
        tk.Label(top,text=APP_NAME,bg="#10182b",fg="#55dfc3",font=("Segoe UI",20,"bold")).pack(side="left",padx=25,pady=18)
        tk.Label(top,text=PUBLISHER,bg="#10182b",fg="#9da9c0").pack(side="left")
        tk.Button(top,text="LOGOUT",command=self.show_auth).pack(side="right",padx=20)
        body=tk.Frame(self,bg="#0b1020"); body.pack(fill="both",expand=True,padx=35,pady=35)
        tk.Label(body,text="Business Analysis Dashboard",bg="#0b1020",fg="white",font=("Segoe UI",28,"bold")).pack(anchor="w")
        tk.Label(body,text="Your workspace is ready. Import business data, analyze it and generate reports.",bg="#0b1020",fg="#9da9c0",font=("Segoe UI",13)).pack(anchor="w",pady=8)
        tk.Button(body,text="IMPORT EXCEL / CSV",command=self.import_file,bg="#55dfc3",fg="#061016",font=("Segoe UI",11,"bold"),relief="flat",padx=20,pady=12).pack(anchor="w",pady=25)
        tk.Label(body,text="Publisher: "+PUBLISHER,bg="#0b1020",fg="#66738e").pack(anchor="w")

    def import_file(self):
        path=filedialog.askopenfilename(filetypes=[("Excel/CSV","*.xlsx *.xls *.csv"),("All files","*.*")])
        if path:
            send_event("file_import_started")
            messagebox.showinfo("Business Analysis","File selected. Connect the analysis modules to process it.")

if __name__=="__main__":
    App().mainloop()
