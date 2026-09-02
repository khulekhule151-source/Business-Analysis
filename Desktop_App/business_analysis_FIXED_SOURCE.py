"""
Business Analysis
Complete single-file Python desktop business analysis application.

Python: 3.11+
Install:
    py -m pip install customtkinter pandas numpy matplotlib openpyxl reportlab

Run:
    py business_analysis.py

Optional CSV/Excel columns:
    Date, Product, Category, Sales, Cost, Quantity, Customer
"""

import os
import sqlite3
import shutil
import sys
import traceback
import requests
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import customtkinter as ctk
    import pandas as pd
    import numpy as np
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except ImportError as exc:
    raise SystemExit(
        "Missing package. Install with:\n"
        "py -m pip install customtkinter pandas numpy matplotlib openpyxl reportlab"
    ) from exc


APP_NAME = "BUSINESS ANALYSIS"
ANALYSIS_API_URL = "https://business-analysis-api-I8nm.onrender.com/api/analyze"
ANALYSIS_API_TIMEOUT = 120
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
EXPORT_DIR = BASE_DIR / "exports"
DB_PATH = DATA_DIR / "business.db"
DATA_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class Database:
    def __init__(self, path=DB_PATH):
        self.path = path
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                product TEXT NOT NULL,
                category TEXT DEFAULT 'General',
                sales REAL DEFAULT 0,
                cost REAL DEFAULT 0,
                quantity INTEGER DEFAULT 1,
                customer TEXT DEFAULT 'Walk-in'
            )
        """)
        self.conn.commit()

    def add(self, row):
        self.conn.execute("""
            INSERT INTO transactions
            (date, product, category, sales, cost, quantity, customer)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, row)
        self.conn.commit()

    def delete(self, record_id):
        self.conn.execute("DELETE FROM transactions WHERE id=?", (record_id,))
        self.conn.commit()

    def dataframe(self):
        return pd.read_sql_query(
            "SELECT * FROM transactions ORDER BY date DESC, id DESC", self.conn
        )

    def replace(self, df):
        required = ["date", "product", "category", "sales", "cost", "quantity", "customer"]
        clean = df.copy()
        for col in required:
            if col not in clean.columns:
                clean[col] = 0 if col in ("sales", "cost", "quantity") else ""
        clean = clean[required].copy()
        self.conn.execute("DELETE FROM transactions")
        for row in clean.itertuples(index=False, name=None):
            self.add(tuple(row))

    def close(self):
        self.conn.close()


class BusinessAnalysisApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1400x850")
        self.minsize(1100, 700)

        self.db = Database()
        self.df = pd.DataFrame()
        self.filtered_df = pd.DataFrame()

        self.colors = {
            "bg": "#0b0f14",
            "panel": "#111820",
            "panel2": "#17212b",
            "text": "#f4f7fb",
            "muted": "#9aa7b4",
            "accent": "#3b82f6",
            "green": "#22c55e",
            "red": "#ef4444",
            "gold": "#f59e0b",
        }

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.build_ui()
        self.load_data()
        self.show_dashboard()

    # ---------- UI ----------
    def build_ui(self):
        self.configure(fg_color=self.colors["bg"])

        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=self.colors["panel"])
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=20, pady=(24, 30))
        ctk.CTkLabel(
            brand, text="BUSINESS ANALYSIS", font=ctk.CTkFont(size=23, weight="bold")
        ).pack(anchor="w")
        ctk.CTkLabel(
            brand, text="Published by Khùlè Khùlè III", text_color=self.colors["muted"],
            font=ctk.CTkFont(size=10, weight="bold")
        ).pack(anchor="w", pady=(3, 0))

        self.nav_buttons = {}
        for name, command in [
            ("Dashboard", self.show_dashboard),
            ("Transactions", self.show_transactions),
            ("Products", self.show_products),
            ("Customers", self.show_customers),
            ("Reports", self.show_reports),
            ("Settings", self.show_settings),
        ]:
            btn = ctk.CTkButton(
                self.sidebar, text=name, command=command, height=42,
                corner_radius=8, anchor="w", fg_color="transparent",
                hover_color=self.colors["panel2"]
            )
            btn.pack(fill="x", padx=14, pady=4)
            self.nav_buttons[name] = btn

        ctk.CTkLabel(
            self.sidebar, text="Local database • SQLite",
            text_color=self.colors["muted"], font=ctk.CTkFont(size=10)
        ).pack(side="bottom", pady=20)

        self.main = ctk.CTkFrame(self, fg_color=self.colors["bg"], corner_radius=0)
        self.main.pack(side="left", fill="both", expand=True)

        self.header = ctk.CTkFrame(self.main, height=74, fg_color="transparent")
        self.header.pack(fill="x", padx=28, pady=(18, 5))
        self.header.pack_propagate(False)

        self.page_title = ctk.CTkLabel(
            self.header, text="Dashboard", font=ctk.CTkFont(size=27, weight="bold")
        )
        self.page_title.pack(side="left", anchor="center")

        tools = ctk.CTkFrame(self.header, fg_color="transparent")
        tools.pack(side="right")
        ctk.CTkButton(tools, text="Import", width=90, command=self.import_file).pack(side="left", padx=4)
        ctk.CTkButton(tools, text="Export", width=90, command=self.export_excel).pack(side="left", padx=4)
        ctk.CTkButton(tools, text="Refresh", width=90, command=self.load_data).pack(side="left", padx=4)

        self.content = ctk.CTkScrollableFrame(self.main, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def clear_content(self, title):
        for child in self.content.winfo_children():
            child.destroy()
        self.page_title.configure(text=title)

    def select_nav(self, name):
        for n, b in self.nav_buttons.items():
            b.configure(fg_color=self.colors["panel2"] if n == name else "transparent")

    def card(self, parent, title, value, subtitle="", accent=None):
        frame = ctk.CTkFrame(parent, fg_color=self.colors["panel"], corner_radius=12)
        ctk.CTkLabel(
            frame, text=title.upper(), text_color=self.colors["muted"],
            font=ctk.CTkFont(size=10, weight="bold")
        ).pack(anchor="w", padx=18, pady=(15, 4))
        ctk.CTkLabel(
            frame, text=value, font=ctk.CTkFont(size=25, weight="bold"),
            text_color=accent or self.colors["text"]
        ).pack(anchor="w", padx=18)
        if subtitle:
            ctk.CTkLabel(
                frame, text=subtitle, text_color=self.colors["muted"],
                font=ctk.CTkFont(size=10)
            ).pack(anchor="w", padx=18, pady=(2, 15))
        return frame

    # ---------- Data ----------
    def load_data(self):
        self.df = self.db.dataframe()
        self.prepare()
        if hasattr(self, "content") and self.page_title.cget("text") == "Dashboard":
            self.show_dashboard()

    def prepare(self):
        if self.df.empty:
            self.filtered_df = self.df.copy()
            return
        self.df["date"] = pd.to_datetime(self.df["date"], errors="coerce")
        for col in ["sales", "cost", "quantity"]:
            self.df[col] = pd.to_numeric(self.df[col], errors="coerce").fillna(0)
        self.df["profit"] = self.df["sales"] - self.df["cost"]
        self.df["margin"] = np.where(
            self.df["sales"] != 0, self.df["profit"] / self.df["sales"] * 100, 0
        )
        self.filtered_df = self.df.copy()

    def _clean_text_value(self, value, fallback="Unknown"):
        """Safely convert imported text to a normal string."""
        if value is None or pd.isna(value):
            return fallback
        value = str(value).strip()
        if not value or value.startswith("<bound method ") or "Series.process" in value:
            return fallback
        return value

    def money(self, value):
        return f"R {value:,.2f}"

    def pct(self, value):
        return f"{value:.1f}%"

    # ---------- Dashboard ----------
    def show_dashboard(self):
        self.select_nav("Dashboard")
        self.clear_content("Dashboard")
        df = self.filtered_df

        if df.empty:
            self.empty_state("No business data yet", "Import an Excel/CSV file or add your first transaction.")
            return

        revenue = df.sales.sum()
        costs = df.cost.sum()
        profit = df.profit.sum()
        margin = profit / revenue * 100 if revenue else 0
        customers = df.customer.nunique()
        transactions = len(df)
        quantity = df.quantity.sum()
        avg = revenue / transactions if transactions else 0

        cards = ctk.CTkFrame(self.content, fg_color="transparent")
        cards.pack(fill="x", pady=(0, 18))
        values = [
            ("Revenue", self.money(revenue), "Total sales", None),
            ("Net Profit", self.money(profit), "Revenue minus cost", self.colors["green"]),
            ("Expenses", self.money(costs), "Total recorded costs", self.colors["gold"]),
            ("Profit Margin", self.pct(margin), "Net profit / revenue", None),
        ]
        for title, value, sub, color in values:
            f = self.card(cards, title, value, sub, color)
            f.pack(side="left", fill="both", expand=True, padx=5)

        mini = ctk.CTkFrame(self.content, fg_color="transparent")
        mini.pack(fill="x", pady=(0, 18))
        for title, value in [
            ("Transactions", f"{transactions:,}"),
            ("Customers", f"{customers:,}"),
            ("Units Sold", f"{quantity:,.0f}"),
            ("Average Transaction", self.money(avg)),
        ]:
            f = self.card(mini, title, value)
            f.pack(side="left", fill="both", expand=True, padx=5)

        chart_row = ctk.CTkFrame(self.content, fg_color="transparent")
        chart_row.pack(fill="both", expand=True)

        left = ctk.CTkFrame(chart_row, fg_color=self.colors["panel"], corner_radius=12)
        left.pack(side="left", fill="both", expand=True, padx=5)
        self.make_revenue_chart(left, df)

        right = ctk.CTkFrame(chart_row, fg_color=self.colors["panel"], corner_radius=12)
        right.pack(side="left", fill="both", expand=True, padx=5)
        self.make_product_chart(right, df)

        rec = ctk.CTkFrame(self.content, fg_color=self.colors["panel"], corner_radius=12)
        rec.pack(fill="x", padx=5, pady=15)
        ctk.CTkLabel(
            rec, text="Business Insights", font=ctk.CTkFont(size=17, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 8))
        for line in self.generate_insights(df):
            ctk.CTkLabel(
                rec, text="• " + line, justify="left", anchor="w",
                text_color=self.colors["muted"]
            ).pack(fill="x", padx=20, pady=2)
        ctk.CTkLabel(rec, text="").pack(pady=3)

    def generate_insights(self, df):
        if df.empty:
            return ["Add data to generate insights."]
        insights = []
        product_sales = df.groupby("product").sales.sum().sort_values(ascending=False)
        cat_profit = df.groupby("category").profit.sum().sort_values(ascending=False)
        best_product = product_sales.index[0]
        insights.append(f"Top product by revenue: {best_product} ({self.money(product_sales.iloc[0])}).")
        if not cat_profit.empty:
            insights.append(f"Most profitable category: {cat_profit.index[0]} ({self.money(cat_profit.iloc[0])}).")
        margin = df.sales.sum() and df.profit.sum() / df.sales.sum() * 100
        insights.append(f"Overall profit margin is {margin:.1f}%.")
        if margin < 15:
            insights.append("Margin is below 15%; review pricing, supplier costs and operating expenses.")
        elif margin >= 30:
            insights.append("Strong margin performance; consider reinvesting part of the profit into growth.")
        if len(df) >= 2:
            recent = df.sort_values("date").groupby(df.sort_values("date").date.dt.to_period("M")).sales.sum()
            if len(recent) >= 2:
                change = (recent.iloc[-1] - recent.iloc[-2]) / recent.iloc[-2] * 100 if recent.iloc[-2] else 0
                direction = "increased" if change >= 0 else "decreased"
                insights.append(f"Latest month revenue {direction} {abs(change):.1f}% versus the previous month.")
        return insights

    # ---------- Charts ----------
    def make_chart(self, parent, title):
        ctk.CTkLabel(
            parent, text=title, font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=18, pady=(15, 0))
        fig = Figure(figsize=(6, 3.2), dpi=100, facecolor=self.colors["panel"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(self.colors["panel"])
        ax.tick_params(colors="#9aa7b4", labelsize=8)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.grid(alpha=0.12)
        fig.tight_layout(pad=1.5)
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        return fig, ax, canvas

    def make_revenue_chart(self, parent, df):
        fig, ax, canvas = self.make_chart(parent, "Revenue & Profit Trend")
        temp = df.dropna(subset=["date"]).copy()
        if temp.empty:
            return
        monthly = temp.groupby(temp.date.dt.to_period("M")).agg(
            Revenue=("sales", "sum"), Profit=("profit", "sum")
        )
        labels = [str(x) for x in monthly.index]
        ax.plot(labels, monthly.Revenue.values, marker="o", label="Revenue")
        ax.plot(labels, monthly.Profit.values, marker="o", label="Profit")
        ax.legend(frameon=False, fontsize=8)
        ax.tick_params(axis="x", rotation=45)
        canvas.draw()

    def make_product_chart(self, parent, df):
        fig, ax, canvas = self.make_chart(parent, "Top Products by Revenue")
        products = df.groupby("product").sales.sum().sort_values(ascending=False).head(8)
        if products.empty:
            return
        ax.barh(list(products.index)[::-1], list(products.values)[::-1])
        ax.tick_params(axis="y", labelsize=8)
        canvas.draw()

    # ---------- Transactions ----------
    def show_transactions(self):
        self.select_nav("Transactions")
        self.clear_content("Transactions")

        toolbar = ctk.CTkFrame(self.content, fg_color=self.colors["panel"], corner_radius=10)
        toolbar.pack(fill="x", pady=(0, 12))
        ctk.CTkButton(toolbar, text="+ Add Transaction", command=self.add_transaction).pack(side="left", padx=12, pady=10)
        ctk.CTkButton(toolbar, text="Import CSV / Excel", command=self.import_file).pack(side="left", padx=4, pady=10)
        ctk.CTkButton(toolbar, text="Delete Selected", command=self.delete_selected).pack(side="left", padx=4, pady=10)
        self.search_var = tk.StringVar()
        search = ctk.CTkEntry(toolbar, textvariable=self.search_var, placeholder_text="Search...", width=220)
        search.pack(side="right", padx=12, pady=10)
        search.bind("<KeyRelease>", lambda e: self.refresh_table())

        frame = ctk.CTkFrame(self.content, fg_color=self.colors["panel"], corner_radius=10)
        frame.pack(fill="both", expand=True)

        columns = ["id", "date", "product", "category", "sales", "cost", "quantity", "customer", "profit", "margin"]
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=22)
        headings = {
            "id": "ID", "date": "Date", "product": "Product", "category": "Category",
            "sales": "Sales", "cost": "Cost", "quantity": "Qty", "customer": "Customer",
            "profit": "Profit", "margin": "Margin"
        }
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=90, anchor="center")
        self.tree.column("product", width=150)
        self.tree.column("customer", width=140)
        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y", pady=10, padx=8)
        self.tree.configure(yscrollcommand=scroll.set)
        self.refresh_table()

    def refresh_table(self):
        if not hasattr(self, "tree"):
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        query = self.search_var.get().lower().strip() if hasattr(self, "search_var") else ""
        df = self.df.copy()
        if query and not df.empty:
            mask = df.astype(str).apply(lambda col: col.str.lower().str.contains(query, na=False))
            df = df[mask.any(axis=1)]
        for _, r in df.iterrows():
            self.tree.insert("", "end", values=(
                int(r.id), r.date.strftime("%Y-%m-%d") if not pd.isna(r.date) else "",
                self._clean_text_value(r.product, "Unknown"),
                self._clean_text_value(r.category, "General"),
                f"{r.sales:,.2f}", f"{r.cost:,.2f}",
                f"{r.quantity:g}", self._clean_text_value(r.customer, "Walk-in"),
                f"{r.profit:,.2f}", f"{r.margin:.1f}%"
            ))

    def add_transaction(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add Transaction")
        dialog.geometry("470x570")
        dialog.transient(self)
        dialog.grab_set()

        fields = {}
        for label, default in [
            ("Date (YYYY-MM-DD)", datetime.now().strftime("%Y-%m-%d")),
            ("Product", ""),
            ("Category", "General"),
            ("Sales", "0"),
            ("Cost", "0"),
            ("Quantity", "1"),
            ("Customer", "Walk-in"),
        ]:
            ctk.CTkLabel(dialog, text=label).pack(anchor="w", padx=30, pady=(13, 3))
            entry = ctk.CTkEntry(dialog, width=410)
            entry.insert(0, default)
            entry.pack(padx=30)
            fields[label] = entry

        def save():
            try:
                date = pd.to_datetime(fields["Date (YYYY-MM-DD)"].get()).strftime("%Y-%m-%d")
                product = fields["Product"].get().strip()
                if not product:
                    raise ValueError("Product is required.")
                row = (
                    date, product, fields["Category"].get().strip() or "General",
                    float(fields["Sales"].get()), float(fields["Cost"].get()),
                    int(float(fields["Quantity"].get())), fields["Customer"].get().strip() or "Walk-in"
                )
                self.db.add(row)
                dialog.destroy()
                self.load_data()
                self.show_transactions()
            except Exception as exc:
                messagebox.showerror("Invalid data", str(exc))

        ctk.CTkButton(dialog, text="Save Transaction", command=save, height=42).pack(pady=25)

    def delete_selected(self):
        if not hasattr(self, "tree"):
            return
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Delete", "Select a transaction first.")
            return
        if not messagebox.askyesno("Confirm", "Delete the selected transaction(s)?"):
            return
        for item in selected:
            values = self.tree.item(item, "values")
            self.db.delete(int(values[0]))
        self.load_data()
        self.show_transactions()

    # ---------- Product / customer analysis ----------
    def show_products(self):
        self.select_nav("Products")
        self.clear_content("Product Analysis")
        df = self.filtered_df
        if df.empty:
            self.empty_state("No product data", "Add or import transactions first.")
            return

        grouped = df.groupby("product").agg(
            Revenue=("sales", "sum"),
            Cost=("cost", "sum"),
            Profit=("profit", "sum"),
            Units=("quantity", "sum"),
            Transactions=("id", "count")
        ).sort_values("Revenue", ascending=False)
        grouped["Margin"] = np.where(grouped.Revenue != 0, grouped.Profit / grouped.Revenue * 100, 0)

        self.analysis_table(grouped.reset_index(), ["product", "Revenue", "Cost", "Profit", "Units", "Transactions", "Margin"])

    def show_customers(self):
        self.select_nav("Customers")
        self.clear_content("Customer Analysis")
        df = self.filtered_df
        if df.empty:
            self.empty_state("No customer data", "Add or import transactions first.")
            return
        grouped = df.groupby("customer").agg(
            Revenue=("sales", "sum"),
            Cost=("cost", "sum"),
            Profit=("profit", "sum"),
            Transactions=("id", "count"),
            Units=("quantity", "sum")
        ).sort_values("Revenue", ascending=False)
        grouped["Average Spend"] = grouped.Revenue / grouped.Transactions
        self.analysis_table(grouped.reset_index(), ["customer", "Revenue", "Cost", "Profit", "Transactions", "Units", "Average Spend"])

    def analysis_table(self, data, cols):
        frame = ctk.CTkFrame(self.content, fg_color=self.colors["panel"], corner_radius=10)
        frame.pack(fill="both", expand=True, padx=5)
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=22)
        for c in cols:
            tree.heading(c, text=c.replace("_", " ").title())
            tree.column(c, width=130, anchor="center")
        tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        scroll.pack(side="right", fill="y", pady=10, padx=8)
        tree.configure(yscrollcommand=scroll.set)
        for _, row in data.iterrows():
            vals = []
            for c in cols:
                v = row[c]
                if c in ("Revenue", "Cost", "Profit", "Average Spend"):
                    vals.append(self.money(float(v)))
                elif c == "Margin":
                    vals.append(self.pct(float(v)))
                elif isinstance(v, (float, np.floating)):
                    vals.append(f"{v:,.2f}")
                else:
                    vals.append(str(v))
            tree.insert("", "end", values=vals)

    # ---------- Reports ----------
    def show_reports(self):
        self.select_nav("Reports")
        self.clear_content("Reports")
        df = self.filtered_df
        panel = ctk.CTkFrame(self.content, fg_color=self.colors["panel"], corner_radius=12)
        panel.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(panel, text="Business Reporting", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", padx=22, pady=(20, 5))
        ctk.CTkLabel(panel, text="Create an Excel or PDF summary from the current business data.", text_color=self.colors["muted"]).pack(anchor="w", padx=22, pady=(0, 18))
        ctk.CTkButton(panel, text="Export Excel Analysis", command=self.export_excel, width=220, height=42).pack(anchor="w", padx=22, pady=6)
        ctk.CTkButton(panel, text="Generate PDF Report", command=self.export_pdf, width=220, height=42).pack(anchor="w", padx=22, pady=(6, 22))

        if not df.empty:
            insights = ctk.CTkFrame(self.content, fg_color=self.colors["panel"], corner_radius=12)
            insights.pack(fill="x", padx=5, pady=15)
            ctk.CTkLabel(insights, text="Executive Summary", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=20, pady=(18, 8))
            for text in self.generate_insights(df):
                ctk.CTkLabel(insights, text="• " + text, text_color=self.colors["muted"]).pack(anchor="w", padx=20, pady=3)

    def export_excel(self):
        df = self.filtered_df.copy()
        if df.empty:
            messagebox.showwarning("Export", "There is no data to export.")
            return
        path = filedialog.asksaveasfilename(
            initialdir=EXPORT_DIR, defaultextension=".xlsx",
            filetypes=[("Excel workbook", "*.xlsx")]
        )
        if not path:
            return
        try:
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Transactions", index=False)
                df.groupby("product").agg(
                    Revenue=("sales", "sum"), Cost=("cost", "sum"),
                    Profit=("profit", "sum"), Units=("quantity", "sum")
                ).sort_values("Revenue", ascending=False).to_excel(writer, sheet_name="Products")
                df.groupby("customer").agg(
                    Revenue=("sales", "sum"), Profit=("profit", "sum"),
                    Transactions=("id", "count")
                ).sort_values("Revenue", ascending=False).to_excel(writer, sheet_name="Customers")
            messagebox.showinfo("Export complete", f"Excel report saved to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export error", str(exc))

    def export_pdf(self):
        df = self.filtered_df.copy()
        if df.empty:
            messagebox.showwarning("Report", "There is no data to report.")
            return
        path = filedialog.asksaveasfilename(
            initialdir=EXPORT_DIR, defaultextension=".pdf",
            filetypes=[("PDF document", "*.pdf")]
        )
        if not path:
            return
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet

            styles = getSampleStyleSheet()
            doc = SimpleDocTemplate(path, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
            revenue, cost, profit = df.sales.sum(), df.cost.sum(), df.profit.sum()
            margin = profit / revenue * 100 if revenue else 0
            story = [
                Paragraph("BUSINESS ANALYSIS", styles["Title"]),
                Paragraph("Published by Khùlè Khùlè III", styles["Normal"]),
                Paragraph(f"Generated: {datetime.now():%Y-%m-%d %H:%M}", styles["Normal"]),
                Spacer(1, 18),
                Paragraph("Executive Summary", styles["Heading2"]),
            ]
            summary = [
                ["Metric", "Value"],
                ["Revenue", self.money(revenue)],
                ["Expenses", self.money(cost)],
                ["Net Profit", self.money(profit)],
                ["Profit Margin", self.pct(margin)],
                ["Transactions", f"{len(df):,}"],
                ["Customers", f"{df.customer.nunique():,}"],
            ]
            table = Table(summary, colWidths=[220, 220])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#17212b")),
                ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
                ("PADDING", (0,0), (-1,-1), 8),
            ]))
            story += [table, Spacer(1, 18), Paragraph("Business Insights", styles["Heading2"])]
            for item in self.generate_insights(df):
                story.append(Paragraph("• " + item, styles["Normal"]))
                story.append(Spacer(1, 5))
            doc.build(story)
            messagebox.showinfo("Report complete", f"PDF report saved to:\n{path}")
        except ImportError:
            messagebox.showerror("Missing package", "Install ReportLab with:\npy -m pip install reportlab")
        except Exception as exc:
            messagebox.showerror("PDF error", str(exc))

    # ---------- Import ----------
    def import_file(self):
        path = filedialog.askopenfilename(
            title="Select Business Data",
            filetypes=[
                ("Business data", "*.csv *.xlsx *.xls"),
                ("CSV files", "*.csv"),
                ("Excel files", "*.xlsx *.xls"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return

        filename = os.path.basename(path)

        # Read locally first so the desktop dashboard can use the data.
        try:
            if path.lower().endswith(".csv"):
                data = pd.read_csv(path)
            elif path.lower().endswith((".xlsx", ".xls")):
                data = pd.read_excel(path)
            else:
                raise ValueError("Unsupported file type. Please select CSV or Excel.")
            if data.empty:
                raise ValueError("The selected file contains no data.")
        except Exception as exc:
            messagebox.showerror("Import Error", f"Could not read the selected file.\n\n{exc}")
            return

        # Upload the original file to the live Render analysis API.
        progress = ctk.CTkToplevel(self)
        progress.title("Business Analysis")
        progress.geometry("480x190")
        progress.resizable(False, False)
        progress.transient(self)
        progress.grab_set()

        ctk.CTkLabel(
            progress, text="Analyzing business data...",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(28, 8))
        ctk.CTkLabel(
            progress, text=f"Uploading {filename}",
            text_color=self.colors["muted"]
        ).pack(pady=5)
        progress_bar = ctk.CTkProgressBar(progress, mode="indeterminate", width=360)
        progress_bar.pack(pady=18)
        progress_bar.start()
        progress.update_idletasks()

        try:
            with open(path, "rb") as file_handle:
                response = requests.post(
                    ANALYSIS_API_URL,
                    files={"file": (filename, file_handle, "application/octet-stream")},
                    timeout=ANALYSIS_API_TIMEOUT,
                )
            progress_bar.stop()
            progress.destroy()
        except requests.exceptions.Timeout:
            progress_bar.stop(); progress.destroy()
            messagebox.showerror("Analysis Timeout", "The Business Analysis API took too long to respond.\n\nPlease try again.")
            return
        except requests.exceptions.ConnectionError:
            progress_bar.stop(); progress.destroy()
            messagebox.showerror("Connection Error", "Could not connect to the Business Analysis API.\n\nCheck your internet connection.")
            return
        except requests.exceptions.RequestException as exc:
            progress_bar.stop(); progress.destroy()
            messagebox.showerror("API Error", f"The analysis request failed.\n\n{exc}")
            return
        except Exception as exc:
            try:
                progress_bar.stop(); progress.destroy()
            except Exception:
                pass
            messagebox.showerror("Analysis Error", f"An unexpected error occurred.\n\n{exc}")
            return

        if response.status_code != 200:
            messagebox.showerror(
                "Analysis API Error",
                "The Business Analysis API returned an error.\n\n"
                f"Status: {response.status_code}\n"
                f"Error: {response.text[:1500]}"
            )
            return

        try:
            result = response.json()
        except ValueError:
            messagebox.showerror("API Response Error", "The API returned an invalid response instead of JSON.")
            return

        if not result.get("success", False):
            messagebox.showerror(
                "Analysis Failed",
                str(result.get("message") or result.get("detail") or result)
            )
            return

        self.analysis_result = result
        self.selected_file = path

        # Normalize the data for the existing local dashboard.
        try:
            data.columns = [str(c).strip().lower().replace(" ", "_") for c in data.columns]
            aliases = {
                "date": ["date", "transaction_date"],
                "product": ["product", "item", "service", "product_name"],
                "category": ["category", "type"],
                "sales": ["sales", "revenue", "amount", "price"],
                "cost": ["cost", "expense", "expenses"],
                "quantity": ["quantity", "qty", "units"],
                "customer": ["customer", "customer_name", "client"],
            }
            rename = {}
            for target, choices in aliases.items():
                for choice in choices:
                    if choice in data.columns:
                        rename[choice] = target
                        break
            data = data.rename(columns=rename)

            required = ["date", "product", "category", "sales", "cost", "quantity", "customer"]
            missing = [c for c in ("date", "product", "sales") if c not in data.columns]
            if missing:
                raise ValueError("Missing required columns: " + ", ".join(missing))

            for col in required:
                if col not in data.columns:
                    if col in ("sales", "cost", "quantity"):
                        data[col] = 0
                    elif col == "category":
                        data[col] = "General"
                    elif col == "customer":
                        data[col] = "Walk-in"
                    else:
                        data[col] = ""

            data["date"] = pd.to_datetime(data["date"], errors="coerce").dt.strftime("%Y-%m-%d")
            data["sales"] = pd.to_numeric(data["sales"], errors="coerce").fillna(0)
            data["cost"] = pd.to_numeric(data["cost"], errors="coerce").fillna(0)
            data["quantity"] = pd.to_numeric(data["quantity"], errors="coerce").fillna(1).astype(int)
            data["product"] = data["product"].apply(lambda v: self._clean_text_value(v, "Unknown"))
            data["category"] = data["category"].apply(lambda v: self._clean_text_value(v, "General"))
            data["customer"] = data["customer"].apply(lambda v: self._clean_text_value(v, "Walk-in"))
            data = data.dropna(subset=["date"])

            if data.empty:
                raise ValueError("No valid business-data rows were found.")

            self.db.replace(data)
            self.load_data()
            self.show_dashboard()
        except Exception as exc:
            messagebox.showerror(
                "Dashboard Import Error",
                f"The API analyzed the file, but the desktop dashboard could not import the data.\n\n{exc}"
            )
            return

        dataset = result.get("dataset", {})
        quality = result.get("data_quality", {})
        original_rows = dataset.get("original_rows", len(data))
        original_columns = dataset.get("original_columns", len(data.columns))
        cleaned_rows = dataset.get("cleaned_rows", len(data))
        cleaned_columns = dataset.get("cleaned_columns", len(data.columns))
        missing_values = quality.get("missing_values", 0)
        duplicate_rows = quality.get("duplicate_rows", 0)

        try:
            send_event_fn = globals().get("send_event")
            if callable(send_event_fn):
                send_event_fn("file_import_completed")
        except Exception:
            pass

        messagebox.showinfo(
            "Analysis Complete",
            f"Business analysis completed successfully.\n\n"
            f"File: {filename}\n\n"
            f"Original rows: {original_rows:,}\n"
            f"Original columns: {original_columns:,}\n"
            f"Cleaned rows: {cleaned_rows:,}\n"
            f"Cleaned columns: {cleaned_columns:,}\n"
            f"Missing values: {missing_values:,}\n"
            f"Duplicate rows: {duplicate_rows:,}\n\n"
            "The results are now loaded into your dashboard."
        )

    # ---------- Settings ----------
    def show_settings(self):
        self.select_nav("Settings")
        self.clear_content("Settings")
        panel = ctk.CTkFrame(self.content, fg_color=self.colors["panel"], corner_radius=12)
        panel.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(panel, text="Application Settings", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", padx=22, pady=(20, 15))

        ctk.CTkLabel(panel, text="Appearance").pack(anchor="w", padx=22, pady=(8, 4))
        mode = ctk.CTkOptionMenu(panel, values=["Dark", "Light", "System"], command=ctk.set_appearance_mode)
        mode.set(ctk.get_appearance_mode())
        mode.pack(anchor="w", padx=22, pady=(0, 15))

        ctk.CTkButton(panel, text="Backup Database", command=self.backup_database, width=190).pack(anchor="w", padx=22, pady=6)
        ctk.CTkButton(panel, text="Clear All Business Data", command=self.clear_database, width=190, fg_color="#b91c1c", hover_color="#991b1b").pack(anchor="w", padx=22, pady=(6, 22))

        info = ctk.CTkFrame(self.content, fg_color=self.colors["panel"], corner_radius=12)
        info.pack(fill="x", padx=5, pady=15)
        ctk.CTkLabel(info, text="Data location", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(18, 3))
        ctk.CTkLabel(info, text=str(DB_PATH), text_color=self.colors["muted"]).pack(anchor="w", padx=20, pady=(0, 18))

    def backup_database(self):
        path = filedialog.asksaveasfilename(
            initialdir=EXPORT_DIR, defaultextension=".db",
            filetypes=[("SQLite database", "*.db")]
        )
        if path:
            try:
                shutil.copy2(DB_PATH, path)
                messagebox.showinfo("Backup", f"Backup saved to:\n{path}")
            except Exception as exc:
                messagebox.showerror("Backup error", str(exc))

    def clear_database(self):
        if not messagebox.askyesno("Delete all data", "This will permanently delete all transactions. Continue?"):
            return
        self.db.conn.execute("DELETE FROM transactions")
        self.db.conn.commit()
        self.load_data()
        self.show_dashboard()

    def empty_state(self, title, message):
        box = ctk.CTkFrame(self.content, fg_color=self.colors["panel"], corner_radius=14)
        box.pack(fill="both", expand=True, padx=5, pady=5)
        ctk.CTkLabel(box, text=title, font=ctk.CTkFont(size=25, weight="bold")).pack(pady=(100, 8))
        ctk.CTkLabel(box, text=message, text_color=self.colors["muted"]).pack(pady=5)
        ctk.CTkButton(box, text="Import Data", command=self.import_file, width=180, height=40).pack(pady=20)

    def on_close(self):
        try:
            self.db.close()
        finally:
            self.destroy()


if __name__ == "__main__":
    try:
        app = BusinessAnalysisApp()
        app.mainloop()
    except Exception:
        traceback.print_exc()
        raise
