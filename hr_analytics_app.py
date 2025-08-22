# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from typing import List, Optional, Dict, Any

# ========================== PAGE SETUP ==========================
st.set_page_config(page_title="HR Analytics Dashboard", layout="wide")

# -------------------------- THEME SWITCH ------------------------
with st.sidebar:
    st.markdown("## Settings")
    dark_mode = st.toggle("Dark Mode", value=True, help="Toggle between Dark and Light themes")
    st.markdown("---")
    st.caption("Tip: use the chart toolbar to download PNGs.")

# Color palettes per section
PALETTES = {
    "demographics": {"seq": px.colors.sequential.Blues,  "primary": "#2563eb"},
    "salaries":     {"seq": px.colors.sequential.Greens, "primary": "#16a34a"},
    "promotions":   {"seq": px.colors.sequential.Purples,"primary": "#7c3aed"},
    "retention":    {"seq": px.colors.sequential.OrRd,   "primary": "#f97316"},
}

UI = {
    "text": "#e5e7eb" if dark_mode else "#0f172a",
    "bg": "#0b1021" if dark_mode else "#ffffff",
    "panel": "#111827" if dark_mode else "#f8fafc",
    "muted": "#9ca3af" if dark_mode else "#475569",
}
PLOTLY_TEMPLATE = "plotly_dark" if dark_mode else "plotly_white"

# Inject basic CSS
st.markdown(f"""
<style>
  .stApp {{ background:{UI['bg']}; color:{UI['text']}; }}
  h1,h2,h3,h4,h5,h6 {{ color:{UI['text']}; }}
  .block-container {{ padding-top: 1rem; }}
  .card {{ background:{UI['panel']}; border-radius:16px; padding:1rem; margin-bottom:1rem; }}
  .desc {{ opacity:.95; }}
  .muted {{ color:{UI['muted']}; font-size:0.95rem; }}
  .stButton>button {{
    background: linear-gradient(90deg, #6366f1 0%, #06b6d4 100%);
    color:white; border:none; border-radius:12px; padding:.55rem 1rem; font-weight:600;
  }}
</style>
""", unsafe_allow_html=True)

# ========================== HELPERS =============================

def to_dt(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce")

def style_fig(fig, section: str, height: Optional[int] = None):
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=UI["text"], size=14),
        margin=dict(l=10, r=10, t=60, b=10),
    )
    if height:
        fig.update_layout(height=height)
    return fig

def safe_cols(df: pd.DataFrame, cols: List[str]) -> bool:
    return set(cols).issubset(df.columns)

@st.cache_data
def latest_per_employee(df: pd.DataFrame, sort_col: str) -> pd.DataFrame:
    if df.empty:
        return df
    if sort_col not in df.columns:
        tmp = df.copy(); tmp[sort_col] = pd.Timestamp("1970-01-01")
    else:
        tmp = df.copy()
    tmp = tmp.sort_values(["employee_id", sort_col])
    return tmp.groupby("employee_id", as_index=False).tail(1)

def add_regression_line(fig: go.Figure, x: np.ndarray, y: np.ndarray, name: str = "Fit") -> None:
    """OLS with numpy polyfit to avoid statsmodels dependency."""
    try:
        ok = ~np.isnan(x) & ~np.isnan(y)
        if ok.sum() < 2:  # not enough points
            return
        m, c = np.polyfit(x[ok], y[ok], 1)
        xs = np.linspace(np.nanmin(x[ok]), np.nanmax(x[ok]), 100)
        ys = m * xs + c
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name=name))
    except Exception:
        # Silent fail to avoid app crash
        pass

def nav_button(label: str, page_value: str, key: str):
    cols = st.columns([1, 1, 1, 1, 1])
    # Spread buttons evenly; pick index based on hash to avoid changing layout
    idx = hash(label) % len(cols)
    with cols[idx]:
        if st.button(label, use_container_width=True, key=key):
            st.session_state["page"] = page_value
            st.query_params["page"] = page_value

def top_nav(active: str):
    st.markdown("### Navigation")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        if st.button("Description", use_container_width=True):
            st.session_state["page"] = "Description"
            st.query_params["page"] = "Description"
    with c2:
        if st.button("Demographics (8)", use_container_width=True):
            st.session_state["page"] = "Demographics"
            st.query_params["page"] = "Demographics"
    with c3:
        if st.button("Salaries (8)", use_container_width=True):
            st.session_state["page"] = "Salaries"
            st.query_params["page"] = "Salaries"
    with c4:
        if st.button("Promotions (7)", use_container_width=True):
            st.session_state["page"] = "Promotions"
            st.query_params["page"] = "Promotions"
    with c5:
        if st.button("Retention (7)", use_container_width=True):
            st.session_state["page"] = "Retention"
            st.query_params["page"] = "Retention"
    st.markdown("---")

def render_card(section: str, title: str, fig=None, table: Optional[pd.DataFrame]=None,
                description: str = "", insights: Optional[List[str]] = None,
                recs: Optional[List[str]] = None, height: Optional[int] = None):
    with st.container():
        st.markdown(f"<div class='card'><h3>{title}</h3>", unsafe_allow_html=True)
        if fig is not None:
            st.plotly_chart(style_fig(fig, section, height=height), use_container_width=True)
        if table is not None:
            st.dataframe(table, use_container_width=True)
        if description:
            st.markdown(f"<p class='desc'><b>Description:</b> {description}</p>", unsafe_allow_html=True)
        if insights:
            st.markdown("**Insights:**")
            for it in insights:
                st.markdown(f"- {it}")
        if recs:
            st.markdown("**Recommendations:**")
            for r in recs:
                st.markdown(f"- {r}")
        st.markdown("</div>", unsafe_allow_html=True)

# ====================== LOAD & PREP DATA ========================
@st.cache_data
def load_data() -> Dict[str, pd.DataFrame]:
    salary = pd.read_csv("salary.csv")
    employee = pd.read_csv("employee.csv")
    cur_snap = pd.read_csv("current_employee_snapshot.csv")
    department = pd.read_csv("department.csv")
    dept_emp = pd.read_csv("department_employee.csv")
    dept_mgr = pd.read_csv("department_manager.csv")
    title = pd.read_csv("title.csv")

    # Normalize dates
    for df, cols in [
        (salary, ["from_date", "to_date"]),
        (dept_emp, ["from_date", "to_date"]),
        (title, ["from_date", "to_date"]),
        (employee, ["birth_date", "hire_date", "termination_date"]),
    ]:
        for c in cols:
            if c in df.columns:
                df[c] = to_dt(df[c])

    # Basic employee frame
    emp = employee.rename(columns={"id": "employee_id"}).copy()
    if "birth_date" in emp.columns:
        emp["age"] = datetime.now().year - emp["birth_date"].dt.year
    else:
        emp["age"] = np.nan

    if "hire_date" in emp.columns:
        emp["company_tenure"] = (pd.Timestamp.today() - emp["hire_date"]).dt.days / 365.25
    else:
        emp["company_tenure"] = np.nan

    # Latest dept
    if safe_cols(dept_emp, ["employee_id", "dept_id"]) and safe_cols(department, ["dept_id", "dept_name"]):
        dept_latest = latest_per_employee(dept_emp, "to_date" if "to_date" in dept_emp.columns else "from_date")
        dept_latest = dept_latest.merge(department, on="dept_id", how="left")[["employee_id", "dept_id", "dept_name"]]
    else:
        dept_latest = cur_snap[[c for c in ["employee_id", "dept_name"] if c in cur_snap.columns]].drop_duplicates()

    # Latest title
    if safe_cols(title, ["employee_id", "title"]):
        title_latest = latest_per_employee(title, "to_date" if "to_date" in title.columns else "from_date")[["employee_id", "title"]]
    else:
        title_latest = cur_snap[[c for c in ["employee_id", "title"] if c in cur_snap.columns]].drop_duplicates()

    # Latest salary
    if safe_cols(salary, ["employee_id", "amount"]):
        sal_latest = latest_per_employee(salary, "from_date" if "from_date" in salary.columns else "amount")[
            ["employee_id", "amount"]
        ].rename(columns={"amount": "latest_salary"})
    else:
        sal_latest = pd.DataFrame(columns=["employee_id", "latest_salary"])

    # Snapshot
    snapshot = (emp
        .merge(dept_latest, on="employee_id", how="left")
        .merge(title_latest, on="employee_id", how="left")
        .merge(sal_latest, on="employee_id", how="left")
    )

    # Bring extra columns from current snapshot if any
    extra_cols = [c for c in cur_snap.columns if c not in snapshot.columns and c != "employee_id"]
    if extra_cols:
        snapshot = snapshot.merge(cur_snap[["employee_id"] + extra_cols], on="employee_id", how="left")

    return {
        "salary": salary,
        "employee": employee,
        "snapshot": snapshot,
        "department": department,
        "dept_emp": dept_emp,
        "dept_mgr": dept_mgr,
        "title": title,
    }

data = load_data()
salary = data["salary"]
employee = data["employee"]
snapshot = data["snapshot"]
department = data["department"]
dept_emp = data["dept_emp"]
dept_mgr = data["dept_mgr"]
title = data["title"]

# Ensure key columns exist to avoid KeyErrors later
for col in ["dept_name", "title", "company_tenure", "age", "latest_salary"]:
    if col not in snapshot.columns:
        snapshot[col] = np.nan

# =========================== HEADER ============================
st.markdown("""
<h1 style='text-align:center;'>HR Analytics Dashboard</h1>
<p style='text-align:center; opacity:.85;'>Description page + 30 interactive charts with insights & recommendations</p>
""", unsafe_allow_html=True)
st.markdown("---")

# ========================= PAGE ROUTING ========================
# Sync state with query params (no deprecated API)
if "page" not in st.session_state:
    st.session_state["page"] = st.query_params.get("page", "Description")

# Guard string type
if isinstance(st.session_state["page"], list):
    st.session_state["page"] = st.session_state["page"][0]

# Top navigation
top_nav(st.session_state["page"])

# ====================== DESCRIPTION PAGE =======================
def render_description():
    st.markdown("## About this program")
    st.markdown(
        """
This dashboard consolidates HR datasets (employees, salaries, titles, departments) and produces
**30 interactive charts** across four pillars: **Demographics**, **Salaries & Compensation**,
**Promotions & Career Growth**, and **Retention & Turnover**.

### Data assumptions
- `employee.csv`: `id`, `birth_date`, `hire_date`, optional `termination_date`, optional `gender`
- `salary.csv`: `employee_id`, `amount`, `from_date`, optional `to_date`
- `title.csv`: `employee_id`, `title`, `from_date`, optional `to_date`
- `department_employee.csv`: `employee_id`, `dept_id`, `from_date`, optional `to_date`
- `department.csv`: `dept_id`, `dept_name`
- `current_employee_snapshot.csv`: optional overrides like `dept_name`, `title`, etc.

The app is resilient to missing columns. Any unavailable metric is **skipped gracefully**.

### How to use
1. Use the **buttons above** to switch sections (also updates URL).
2. Use the **Dark Mode** toggle in the sidebar for light/dark theming.
3. Each card includes a **Description**, **Insights**, and **Recommendations** to help you interpret results.

### Performance tips
- Charts are rendered only for the active section to keep the app responsive.
- Extremely large CSVs may benefit from pre-aggregations outside the app.
        """.strip()
    )

# ========================= DEMOGRAPHICS (8) =====================
def render_demographics():
    pal = PALETTES["demographics"]
    # 1) Age distribution
    if "age" in snapshot.columns:
        s = snapshot["age"].dropna().astype(int)
        if not s.empty:
            age_counts = s.value_counts().sort_index().reset_index()
            age_counts.columns = ["Age", "Count"]
            fig = px.bar(age_counts, x="Age", y="Count", color="Count", color_continuous_scale=pal["seq"])
            render_card("demographics", "Age Distribution", fig,
                        description="Distribution of current employees by age (years).",
                        insights=["Identify dominant age bands and gaps."],
                        recs=["Tailor benefits and learning paths by age segment."])

    # 2) Age group composition by department
    if safe_cols(snapshot, ["age", "dept_name"]):
        df = snapshot.dropna(subset=["age", "dept_name"]).copy()
        if not df.empty:
            df["age_group"] = pd.cut(df["age"], bins=[10,20,30,40,50,60,70],
                                     labels=["10s","20s","30s","40s","50s","60s"], right=False)
            grp = df.pivot_table(index="dept_name", columns="age_group", values="employee_id",
                                 aggfunc="count", fill_value=0).reset_index()
            fig = px.bar(grp, x="dept_name", y=grp.columns[1:], barmode="stack",
                         color_discrete_sequence=pal["seq"])
            fig.update_xaxes(tickangle=45)
            render_card("demographics", "Age Group Composition by Department", fig,
                        description="Stacked headcount by age group for each department.",
                        insights=["Departments with skewed age structures are visible."],
                        recs=["Balance hiring to reduce succession risk."])

    # 3) Headcount by department
    if "dept_name" in snapshot.columns:
        dept_dist = snapshot["dept_name"].dropna().value_counts().reset_index()
        if not dept_dist.empty:
            dept_dist.columns = ["Department", "Headcount"]
            fig = px.bar(dept_dist, x="Department", y="Headcount", color="Headcount",
                         color_continuous_scale=pal["seq"])
            render_card("demographics", "Headcount by Department", fig,
                        description="Current headcount by department.",
                        insights=["Capacity hotspots and understaffed units."],
                        recs=["Align hiring plans with workload & revenue impact."])

    # 4) Headcount by job title (Top 20)
    if "title" in snapshot.columns:
        title_counts = snapshot["title"].fillna("Unknown").value_counts().head(20).reset_index()
        if not title_counts.empty:
            title_counts.columns = ["Title", "Headcount"]
            fig = px.bar(title_counts, x="Title", y="Headcount", color="Headcount",
                         color_continuous_scale=pal["seq"])
            fig.update_xaxes(tickangle=45)
            render_card("demographics", "Headcount by Job Title (Top 20)", fig,
                        description="Most common roles across the organization.",
                        insights=["Dominant roles and single-point dependencies."],
                        recs=["Cross-train and plan backups for critical roles."])

    # 5) Age by department (box)
    if safe_cols(snapshot, ["age", "dept_name"]):
        df = snapshot.dropna(subset=["age", "dept_name"])
        if not df.empty:
            fig = px.box(df, x="dept_name", y="age", color="dept_name")
            fig.update_xaxes(tickangle=45, title="")
            render_card("demographics", "Age Distribution by Department (Box)", fig,
                        description="Spread and median age by department.",
                        insights=["Outlier-heavy teams may need tailored wellbeing programs."],
                        recs=["Review workload design for teams with wide age spread."])

    # 6) Gender mix overall
    gcol = next((c for c in ["gender", "sex", "Gender", "Sex"] if c in snapshot.columns), None)
    if gcol:
        counts = snapshot[gcol].value_counts().reset_index()
        if not counts.empty:
            counts.columns = ["Gender", "Count"]
            fig = px.pie(counts, names="Gender", values="Count")
            render_card("demographics", "Gender Mix (Overall)", fig,
                        description="Gender composition across the company.",
                        insights=["Detect imbalance and track diversity goals."],
                        recs=["Widen sourcing channels and ensure unbiased screening."])

    # 7) Gender by department
    if gcol and "dept_name" in snapshot.columns:
        gdept = snapshot[[gcol, "dept_name"]].dropna()
        if not gdept.empty:
            gdept = gdept.value_counts().reset_index(name="Count")
            gdept.rename(columns={gcol: "Gender"}, inplace=True)
            fig = px.bar(gdept, x="dept_name", y="Count", color="Gender", barmode="stack")
            render_card("demographics", "Gender Ratio by Department", fig,
                        description="Gender distribution per department.",
                        insights=["Spot departments with skewed ratios."],
                        recs=["Set local targets and mentorship for underrepresented groups."])

    # 8) New hires per year
    if "hire_date" in employee.columns:
        hires = employee.rename(columns={"id": "employee_id"}).copy()
        hires["year"] = to_dt(hires["hire_date"]).dt.year
        by_year = hires["year"].value_counts().sort_index().reset_index()
        if not by_year.empty:
            by_year.columns = ["Year", "New Hires"]
            fig = px.bar(by_year, x="Year", y="New Hires", color="New Hires",
                         color_continuous_scale=pal["seq"])
            render_card("demographics", "New Hires per Year", fig,
                        description="Number of employees hired each year.",
                        insights=["Hiring cycles and seasonality."],
                        recs=["Plan recruiting sprints ahead of seasonal peaks."])

# ===================== SALARIES & COMPENSATION (8) =============
def render_salaries():
    pal = PALETTES["salaries"]

    # helper: latest salary per employee
    latest_sal = pd.DataFrame()
    if safe_cols(salary, ["employee_id", "amount"]):
        latest_sal = latest_per_employee(salary, "from_date" if "from_date" in salary.columns else "amount")

    # 1) Average salary over time
    if safe_cols(salary, ["amount", "from_date"]):
        df = salary.copy()
        df["from_date"] = to_dt(df["from_date"])
        df["year"] = df["from_date"].dt.year
        avg_salary_per_year = df.groupby("year")["amount"].mean().reset_index()
        if not avg_salary_per_year.empty:
            fig = px.line(avg_salary_per_year, x="year", y="amount", markers=True)
            render_card("salaries", "Average Salary Over Time", fig,
                        description="Year-over-year average compensation.",
                        insights=["Identify acceleration or stagnation in pay growth."],
                        recs=["Budget merit increases aligned with market benchmarks."])

    # 2) Top 20 salaries (table)
    if safe_cols(salary, ["employee_id", "amount"]):
        top = salary.groupby("employee_id")["amount"].max().sort_values(ascending=False).head(20).reset_index()
        if not top.empty:
            top.columns = ["Employee ID", "Top Salary"]
            render_card("salaries", "Top 20 Salaries (Table)", None,
                        table=top.style.format({"Top Salary": "{:,.0f}"}).data,
                        description="Highest recorded salary per employee.",
                        insights=["Outliers and executive bands."],
                        recs=["Ensure pay governance and internal parity checks."])

    # 3) Salary histogram (latest)
    if not latest_sal.empty:
        fig = px.histogram(latest_sal, x="amount", nbins=40, color_discrete_sequence=[pal["primary"]])
        render_card("salaries", "Salary Distribution (Latest)", fig,
                    description="Histogram of the latest salary amounts.",
                    insights=["Skewness indicates band compression or outliers."],
                    recs=["Review ranges; consider mid-point corrections."])

    # 4) Avg salary by department
    if "dept_name" in snapshot.columns and not latest_sal.empty:
        base = snapshot[["employee_id", "dept_name"]].dropna()
        if not base.empty:
            merged = base.merge(latest_sal[["employee_id", "amount"]], on="employee_id", how="left").dropna()
            if not merged.empty:
                dept_avg = merged.groupby("dept_name")["amount"].mean().reset_index().sort_values("amount", ascending=False)
                fig = px.bar(dept_avg, x="dept_name", y="amount", color="amount", color_continuous_scale=pal["seq"])
                fig.update_xaxes(tickangle=45)
                render_card("salaries", "Average Salary by Department", fig,
                            description="Mean compensation per department.",
                            insights=["High-paying functions vs support units."],
                            recs=["Benchmark against market; adjust for critical roles."])

    # 5) Tenure vs salary (scatter + fit)
    if "company_tenure" in snapshot.columns and not latest_sal.empty:
        m = snapshot[["employee_id", "company_tenure"]].merge(
            latest_sal[["employee_id", "amount"]], on="employee_id", how="left"
        ).dropna()
        if not m.empty:
            fig = px.scatter(m, x="company_tenure", y="amount")
            add_regression_line(fig, m["company_tenure"].to_numpy(), m["amount"].to_numpy(), name="OLS (np)")
            render_card("salaries", "Tenure vs Salary (Latest)", fig,
                        description="Relationship between years in company and current pay.",
                        insights=["Weak correlation may signal pay policy issues."],
                        recs=["Define progression bands tied to tenure and performance."])

    # 6) Top 10 salary growth %
    if safe_cols(salary, ["employee_id", "amount"]):
        g = salary.groupby("employee_id")["amount"].agg(["min", "max"]).reset_index()
        g = g[g["min"] > 0]
        if not g.empty:
            g["growth_%"] = ((g["max"] - g["min"]) / g["min"]) * 100
            topg = g.sort_values("growth_%", ascending=False).head(10)
            fig = px.bar(topg, x="employee_id", y="growth_%", color="growth_%", color_continuous_scale=pal["seq"])
            render_card("salaries", "Top 10 Salary Growth %", fig,
                        description="Largest percentage increase from first to latest salary.",
                        insights=["Fast-trackers or compression adjustments."],
                        recs=["Audit fairness; align with performance outcomes."])

    # 7) Salary spread by department (strip)
    if "dept_name" in snapshot.columns and not latest_sal.empty:
        base = snapshot[["employee_id", "dept_name"]]
        merged = base.merge(latest_sal[["employee_id", "amount"]], on="employee_id", how="left").dropna()
        if not merged.empty:
            fig = px.strip(merged, x="dept_name", y="amount", color="dept_name")
            fig.update_xaxes(tickangle=45)
            render_card("salaries", "Salary Spread by Department", fig,
                        description="Point distribution of latest salaries per department.",
                        insights=["Identify outliers and band overlaps."],
                        recs=["Standardize ranges; review exception approvals."])

    # 8) Average salary by title (Top 30)
    if "title" in snapshot.columns and not latest_sal.empty:
        base = snapshot[["employee_id", "title"]].copy()
        base["title"] = base["title"].fillna("Unknown")
        merged = base.merge(latest_sal[["employee_id", "amount"]], on="employee_id", how="left").dropna()
        if not merged.empty:
            avg_t = merged.groupby("title")["amount"].mean().reset_index().sort_values("amount", ascending=False).head(30)
            fig = px.bar(avg_t, x="title", y="amount")
            fig.update_xaxes(tickangle=45, title="")
            render_card("salaries", "Average Salary by Job Title (Top 30)", fig,
                        description="Mean latest pay for the top 30 titles.",
                        insights=["Identify premium roles and pay gaps."],
                        recs=["Run pay equity analysis within similar bands."])

# ================= PROMOTIONS & CAREER GROWTH (7) ==============
def render_promotions():
    pal = PALETTES["promotions"]

    promos = None
    if safe_cols(title, ["employee_id", "title", "from_date"]):
        tdf = title.copy()
        tdf["from_date"] = to_dt(tdf["from_date"])
        tdf = tdf.sort_values(["employee_id", "from_date"])
        tdf["prev_title"] = tdf.groupby("employee_id")["title"].shift()
        tdf["changed"] = (tdf["title"] != tdf["prev_title"]).astype(int)
        promos = tdf.groupby("employee_id")["changed"].sum().reset_index(name="promotion_count")
        tdf["year"] = tdf["from_date"].dt.year

        # 1) Promotions per year
        per_year = tdf[tdf["changed"] == 1].groupby("year").size().reset_index(name="Promotions")
        if not per_year.empty:
            fig = px.bar(per_year, x="year", y="Promotions", color="Promotions",
                         color_continuous_scale=pal["seq"])
            render_card("promotions", "Promotions per Year", fig,
                        description="Count of title changes by year.",
                        insights=["Waves of career moves; hiring vs promotion strategy."],
                        recs=["Stabilize cadence with clear career frameworks."])

        # 2) Time to first promotion (years)
        if "hire_date" in employee.columns:
            first_change = (tdf[tdf["changed"] == 1]
                            .groupby("employee_id")["from_date"]
                            .min().reset_index().rename(columns={"from_date": "first_promo_date"}))
            tmp = (employee.rename(columns={"id": "employee_id"})[["employee_id", "hire_date"]]
                   .merge(first_change, on="employee_id", how="inner"))
            tmp["time_to_first_promo_years"] = (to_dt(tmp["first_promo_date"]) - to_dt(tmp["hire_date"])).dt.days / 365.25
            if not tmp.empty:
                fig = px.histogram(tmp, x="time_to_first_promo_years", nbins=30,
                                   color_discrete_sequence=[pal["primary"]])
                render_card("promotions", "Time to First Promotion (Years)", fig,
                            description="Distribution of tenure before first promotion.",
                            insights=["Long lags may harm retention of top talent."],
                            recs=["Publish SLA for promotion timelines and criteria."])

        # 3) Promotions by department (total)
        if "dept_name" in snapshot.columns:
            pmap = promos.merge(snapshot[["employee_id", "dept_name"]], on="employee_id", how="left")
            by_dept = pmap.groupby("dept_name")["promotion_count"].sum().reset_index().sort_values("promotion_count", ascending=False)
            if not by_dept.empty:
                fig = px.bar(by_dept, x="dept_name", y="promotion_count", color="promotion_count",
                             color_continuous_scale=pal["seq"])
                fig.update_xaxes(tickangle=45)
                render_card("promotions", "Promotions by Department (Total)", fig,
                            description="Total number of promotions mapped to current departments.",
                            insights=["Career-progressive units vs flat structures."],
                            recs=["Create internal mobility lanes in flat units."])

        # 4) Employees with multiple promotions (Top 20)
        top_multi = promos.sort_values("promotion_count", ascending=False).head(20)
        if not top_multi.empty:
            fig = px.bar(top_multi, x="employee_id", y="promotion_count", color="promotion_count",
                         color_continuous_scale=pal["seq"])
            render_card("promotions", "Employees with Multiple Promotions (Top 20)", fig,
                        description="Employees who recorded the most title changes.",
                        insights=["High-trajectory talent clusters."],
                        recs=["Design leadership programs for high-potentials."])

        # 5) Promotions by gender
        gcol = next((c for c in ["gender", "sex", "Gender", "Sex"] if c in snapshot.columns), None)
        if gcol:
            m = promos.merge(snapshot[["employee_id", gcol]], on="employee_id", how="left")
            by_g = m.groupby(gcol)["promotion_count"].sum().reset_index().rename(columns={gcol: "Gender"})
            if not by_g.empty:
                fig = px.bar(by_g, x="Gender", y="promotion_count", color="promotion_count",
                             color_continuous_scale=pal["seq"])
                render_card("promotions", "Promotions by Gender", fig,
                            description="Total promotions aggregated by gender.",
                            insights=["Detect bias or pipeline gaps."],
                            recs=["Run calibrated promotion panels; track ratios quarterly."])

        # 6) Career path length (title steps)
        path_len = title.groupby("employee_id").size().reset_index(name="title_steps")
        if not path_len.empty:
            fig = px.histogram(path_len, x="title_steps", nbins=20, color_discrete_sequence=[pal["primary"]])
            render_card("promotions", "Career Path Length (Title Steps)", fig,
                        description="How many title records per employee (proxy for moves).",
                        insights=["Flat paths vs dynamic careers."],
                        recs=["Offer lateral moves where vertical ladders are short."])

        # 7) Promotions heatmap (dept × year)
        if "dept_name" in snapshot.columns:
            mm = tdf[tdf["changed"] == 1].merge(snapshot[["employee_id", "dept_name"]], on="employee_id", how="left")
            if not mm.empty:
                heat = mm.pivot_table(index="dept_name", columns="year", values="employee_id",
                                      aggfunc="count", fill_value=0)
                fig = px.imshow(heat, aspect="auto", color_continuous_scale=pal["seq"])
                render_card("promotions", "Promotions Heatmap (Dept × Year)", fig,
                            description="Where and when promotions cluster.",
                            insights=["Timing and departmental cadence of promotions."],
                            recs=["Smooth promotion cycles to reduce churn risk."])

# ====================== RETENTION & TURNOVER (7) ===============
def render_retention():
    pal = PALETTES["retention"]

    # 1) Tenure distribution
    if "company_tenure" in snapshot.columns:
        df = snapshot.dropna(subset=["company_tenure"])
        if not df.empty:
            fig = px.histogram(df, x="company_tenure", nbins=40, color_discrete_sequence=[pal["primary"]])
            render_card("retention", "Tenure Distribution (Years)", fig,
                        description="Histogram of employee time in company.",
                        insights=["Heavy early churn or long-tenured core."],
                        recs=["Target onboarding/mentorship to reduce early exits."])

    # 2) Tenure by department (box)
    if safe_cols(snapshot, ["dept_name", "company_tenure"]):
        df = snapshot.dropna(subset=["dept_name", "company_tenure"])
        if not df.empty:
            fig = px.box(df, x="dept_name", y="company_tenure", color="dept_name")
            fig.update_xaxes(tickangle=45, title="")
            render_card("retention", "Tenure by Department (Box)", fig,
                        description="Spread and median tenure by department.",
                        insights=["Units with systematic early churn."],
                        recs=["Audit managers' onboarding and workload allocation."])

    # 3) New hires per year (again for retention trendline view)
    if "hire_date" in employee.columns:
        hires = employee.rename(columns={"id": "employee_id"}).copy()
        hires["year"] = to_dt(hires["hire_date"]).dt.year
        by_year = hires["year"].value_counts().sort_index().reset_index()
        if not by_year.empty:
            by_year.columns = ["Year", "New Hires"]
            fig = px.bar(by_year, x="Year", y="New Hires", color="New Hires",
                         color_continuous_scale=pal["seq"])
            render_card("retention", "New Hires per Year", fig,
                        description="Annual intake volume.",
                        insights=["Scaling phases and hiring freezes."],
                        recs=["Capacity plan recruiting with business cycles."])

    # 4) Terminations per year
    if "termination_date" in employee.columns:
        terms = employee.rename(columns={"id": "employee_id"}).copy()
        terms["year"] = to_dt(terms["termination_date"]).dt.year
        terms = terms.dropna(subset=["year"])
        if not terms.empty:
            terms_y = terms["year"].value_counts().sort_index().reset_index()
            terms_y.columns = ["Year", "Terminations"]
            fig = px.bar(terms_y, x="Year", y="Terminations", color="Terminations",
                         color_continuous_scale=pal["seq"])
            render_card("retention", "Terminations per Year", fig,
                        description="Annual employee exits (if data available).",
                        insights=["Attrition spikes / stabilization."],
                        recs=["Root-cause analysis during spikes; manager coaching."])

    # 5) Attrition rate by department
    if "dept_name" in snapshot.columns and "termination_date" in employee.columns:
        active = snapshot[["employee_id", "dept_name"]]
        terms = employee.rename(columns={"id": "employee_id"})[["employee_id", "termination_date"]]
        mm = active.merge(terms, on="employee_id", how="left")
        if not mm.empty:
            mm["has_left"] = mm["termination_date"].notna().astype(int)
            rate = mm.groupby("dept_name")["has_left"].mean().reset_index().rename(columns={"has_left": "attrition_rate"})
            fig = px.bar(rate, x="dept_name", y="attrition_rate", color="attrition_rate", color_continuous_scale=pal["seq"])
            fig.update_xaxes(tickangle=45)
            render_card("retention", "Attrition Rate by Department", fig,
                        description="Share of employees with termination record per department.",
                        insights=["At-risk teams."],
                        recs=["Early-warning dashboards & stay interviews."])

    # 6) Tenure vs salary (heatmap)
    if "company_tenure" in snapshot.columns and safe_cols(salary, ["employee_id", "amount"]):
        latest_sal = latest_per_employee(salary, "from_date" if "from_date" in salary.columns else "amount")
        mm = snapshot[["employee_id", "company_tenure"]].merge(
            latest_sal[["employee_id", "amount"]], on="employee_id", how="left"
        ).dropna()
        if not mm.empty:
            fig = px.density_heatmap(mm, x="company_tenure", y="amount", nbinsx=25, nbinsy=25,
                                     color_continuous_scale=pal["seq"])
            render_card("retention", "Tenure vs Salary (Heatmap)", fig,
                        description="Joint distribution of tenure and pay.",
                        insights=["Plateaus or rapid pay growth with tenure."],
                        recs=["Define step increases & promotions to reduce plateaus."])

    # 7) Department moves per employee
    if "employee_id" in dept_emp.columns:
        counts = dept_emp.groupby("employee_id").size().reset_index(name="dept_moves")
        if not counts.empty:
            moves = counts["dept_moves"].value_counts().reset_index()
            moves.columns = ["Moves", "Employees"]
            fig = px.bar(moves, x="Moves", y="Employees", color="Employees",
                         color_continuous_scale=pal["seq"])
            render_card("retention", "Department Moves per Employee", fig,
                        description="How many department records per employee (proxy for transfers).",
                        insights=["Internal mobility health."],
                        recs=["Advertise internal roles; simplify transfer policy."])

# ========================== RENDER PAGES ========================
page = st.session_state["page"]
if page == "Description":
    render_description()
elif page == "Demographics":
    render_demographics()
elif page == "Salaries":
    render_salaries()
elif page == "Promotions":
    render_promotions()
elif page == "Retention":
    render_retention()
else:
    # Fallback to description if unknown param
    st.session_state["page"] = "Description"
    st.query_params["page"] = "Description"
    render_description()

st.markdown("<div class='muted'>Render complete. Use the navigation buttons above to switch sections.</div>", unsafe_allow_html=True)
