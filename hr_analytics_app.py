# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# -------------------- Page config --------------------
st.set_page_config(page_title="HR Analytics Dashboard", layout="wide")

# -------------------- Theme & palettes --------------------
with st.sidebar:
    st.header("Settings")
    DARK_MODE = st.toggle("Dark mode", value=True)
    st.markdown("Use the controls below to navigate pages and download charts.")

PLOTLY_TEMPLATE = "plotly_dark" if DARK_MODE else "plotly_white"
TEXT_COLOR = "#e5e7eb" if DARK_MODE else "#0f172a"
BG_COLOR = "#0b1021" if DARK_MODE else "#ffffff"
PANEL_COLOR = "#111827" if DARK_MODE else "#f8fafc"

PALETTES = {
    "demographics": {"seq": px.colors.sequential.Blues, "primary": "#0284c7"},
    "salaries": {"seq": px.colors.sequential.Greens, "primary": "#16a34a"},
    "promotions": {"seq": px.colors.sequential.Purples, "primary": "#7c3aed"},
    "retention": {"seq": px.colors.sequential.OrRd, "primary": "#f97316"},
}

# Inject lightweight CSS for panels and colors
st.markdown(
    f"""
<style>
    .stApp {{ background:{BG_COLOR}; color:{TEXT_COLOR}; }}
    .card {{ background:{PANEL_COLOR}; padding:16px; border-radius:12px; margin-bottom:12px; }}
    h1,h2,h3 {{ color:{TEXT_COLOR} !important; }}
    .muted {{ opacity:0.85; font-size:0.95rem; }}
    .nav-btn {{ margin:6px; }}
</style>
""",
    unsafe_allow_html=True,
)

# -------------------- Helpers --------------------
def to_dt(s):
    return pd.to_datetime(s, errors="coerce")

@st.cache_data
def load_csv_safe(path):
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

def ensure_columns(df, cols):
    """Ensure columns exist in df. For date-like columns we put NaT, else NaN."""
    for c in cols:
        if c not in df.columns:
            # If name suggests date store NaT
            if "date" in c or "hire" in c or "termination" in c or "from_date" in c or "to_date" in c:
                df[c] = pd.NaT
            else:
                df[c] = np.nan
    return df

def latest_per_employee(df, date_col):
    """Return last record per employee according to date_col; if date_col missing use row order."""
    df = df.copy()
    if date_col not in df.columns:
        # create artificial date to preserve grouping
        df["_art_date"] = pd.Timestamp("1970-01-01")
        date_col = "_art_date"
    df[date_col] = to_dt(df[date_col])
    df = df.sort_values(["employee_id", date_col])
    return df.groupby("employee_id", as_index=False).tail(1)

def style_plotly(fig, title=None, height=None):
    fig.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    if title:
        fig.update_layout(title=dict(text=title, x=0.02, xanchor="left"))
    if height:
        fig.update_layout(height=height)
    return fig

def render_card(title, fig=None, table=None, description="", insights=None, recommendations=None):
    st.markdown(f"<div class='card'><h3>{title}</h3>", unsafe_allow_html=True)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    if table is not None:
        st.dataframe(table, use_container_width=True)
    if description:
        st.markdown(f"**Description:** {description}")
    if insights:
        st.markdown("**Insights:**")
        for it in insights:
            st.markdown(f"- {it}")
    if recommendations:
        st.markdown("**Recommendations:**")
        for r in recommendations:
            st.markdown(f"- {r}")
    st.markdown("</div>", unsafe_allow_html=True)

# -------------------- Load data (safe) --------------------
salary = load_csv_safe("salary.csv")
employee = load_csv_safe("employee.csv")
current_snapshot = load_csv_safe("current_employee_snapshot.csv")
department = load_csv_safe("department.csv")
department_employee = load_csv_safe("department_employee.csv")
department_manager = load_csv_safe("department_manager.csv")
title = load_csv_safe("title.csv")

# Ensure common columns exist to avoid KeyError
employee = ensure_columns(employee, ["id", "birth_date", "hire_date", "termination_date"])
salary = ensure_columns(salary, ["employee_id", "amount", "from_date", "to_date"])
current_snapshot = ensure_columns(current_snapshot, ["employee_id", "dept_name", "title", "salary_amount", "age", "company_tenure"])
department_employee = ensure_columns(department_employee, ["employee_id", "dept_id", "from_date", "to_date"])
department = ensure_columns(department, ["dept_id", "dept_name"])
title = ensure_columns(title, ["employee_id", "title", "from_date", "to_date"])

# Normalize employee id column name
if "id" in employee.columns and "employee_id" not in employee.columns:
    employee = employee.rename(columns={"id":"employee_id"})

# compute age and tenure if possible
if "birth_date" in employee.columns:
    employee["birth_date"] = to_dt(employee["birth_date"])
    employee["age"] = employee["birth_date"].dt.year.map(lambda y: datetime.now().year - y if pd.notna(y) else np.nan)
if "hire_date" in employee.columns:
    employee["hire_date"] = to_dt(employee["hire_date"])
    employee["company_tenure"] = (pd.Timestamp.today() - employee["hire_date"]).dt.days/365.25

# Build snapshot merged table (one row per employee) by joining latest dept/title/salary
# latest dept
if {"employee_id", "dept_id"}.issubset(department_employee.columns) and {"dept_id","dept_name"}.issubset(department.columns):
    dept_latest = latest_per_employee(department_employee.merge(department, on="dept_id", how="left"), "to_date" if "to_date" in department_employee.columns else "from_date")
    dept_latest = dept_latest[["employee_id", "dept_name"]]
else:
    dept_latest = current_snapshot[["employee_id","dept_name"]].drop_duplicates() if {"employee_id","dept_name"}.issubset(current_snapshot.columns) else pd.DataFrame(columns=["employee_id","dept_name"])

# latest title
if {"employee_id","title"}.issubset(title.columns):
    title_latest = latest_per_employee(title, "to_date" if "to_date" in title.columns else "from_date")[["employee_id","title"]]
else:
    title_latest = current_snapshot[["employee_id","title"]].drop_duplicates() if {"employee_id","title"}.issubset(current_snapshot.columns) else pd.DataFrame(columns=["employee_id","title"])

# latest salary
if {"employee_id","amount"}.issubset(salary.columns):
    salary_latest = latest_per_employee(salary, "from_date" if "from_date" in salary.columns else "to_date")[["employee_id","amount"]].rename(columns={"amount":"latest_salary"})
else:
    salary_latest = pd.DataFrame(columns=["employee_id","latest_salary"])

# Base employee frame
if "employee_id" not in employee.columns:
    # fall back to using current_snapshot ids if present
    if "employee_id" in current_snapshot.columns:
        base_emp = current_snapshot[["employee_id"]].drop_duplicates().assign(age=np.nan, company_tenure=np.nan)
    else:
        base_emp = pd.DataFrame(columns=["employee_id"])
else:
    base_emp = employee.copy()

# Merge to form unified snapshot
snapshot = base_emp.merge(dept_latest, on="employee_id", how="left") \
                   .merge(title_latest, on="employee_id", how="left") \
                   .merge(salary_latest, on="employee_id", how="left")

# Bring extras from current_snapshot if present
if "employee_id" in current_snapshot.columns:
    extras = [c for c in current_snapshot.columns if c not in snapshot.columns and c != "employee_id"]
    if extras:
        snapshot = snapshot.merge(current_snapshot[["employee_id"] + extras], on="employee_id", how="left")

# Ensure key columns exist in snapshot
for c in ["dept_name","title","company_tenure","age","latest_salary"]:
    if c not in snapshot.columns:
        snapshot[c] = np.nan

# -------------------- UI: Pages & bottom navigation --------------------
PAGES = ["About", "Demographics", "Salaries", "Promotions", "Retention"]
if "page_index" not in st.session_state:
    st.session_state.page_index = 0

# Top selector for quick jumps
page = st.sidebar.radio("Page", PAGES, index=st.session_state.page_index)

# keep session_state aligned with sidebar selection
st.session_state.page_index = PAGES.index(page)

# Header
st.title("HR Analytics Dashboard")
st.markdown("30 interactive charts. Each chart contains Description → Insights → Recommendations.")
st.markdown("---")

# -------------------- About page --------------------
def render_about():
    st.header("About this Dashboard")
    st.markdown(
        """
**Purpose:** This dashboard provides a consolidated view of workforce, compensation,
promotions, and retention metrics to help HR and business leaders make data-driven decisions.

**Features**
- 30 interactive charts across 4 sections (Demographics, Salaries, Promotions, Retention).
- Light/Dark theme.
- Safe handling for missing columns in CSVs.
- Descriptions, actionable insights, and recommendations below every chart.
- Download charts via Plotly modebar.

**Data Required (recommended)**
- `employee.csv` with columns: `id` or `employee_id`, `birth_date`, `hire_date`, `termination_date`, optional `gender`.
- `salary.csv` with columns: `employee_id`, `amount`, `from_date`, `to_date`.
- `title.csv` with columns: `employee_id`, `title`, `from_date`, `to_date`.
- `department_employee.csv` + `department.csv` for department history and names.
- `current_employee_snapshot.csv` is optional but helpful.

**How to use**
1. Upload CSV files into the app folder.
2. Use sidebar to switch pages and theme.
3. Click Previous / Next at the bottom to navigate pages quickly.

**Limitations**
- Missing or malformed columns are handled gracefully, but charts depending on them will show limited results.
- This is a single-file app for convenience; consider modularization for large datasets.

**Contact**
If you need customization (filters, export, automated refresh), modify the code or request enhancements.
        """
    )

# -------------------- Demographics (8 charts) --------------------
def render_demographics():
    pal = PALETTES["demographics"]
    st.header("Demographics")

    # 1 Age histogram
    if "age" in snapshot.columns and snapshot["age"].notna().any():
        df = snapshot.dropna(subset=["age"])
        fig = px.histogram(df, x="age", nbins=40, color_discrete_sequence=[pal["primary"]])
        fig = style_plotly(fig, "Age Distribution")
        render_card(
            "Age Distribution",
            fig,
            description="Histogram of employee ages.",
            insights=["Shows dominant age cohorts and outliers."],
            recommendations=["Tailor learning & benefits to dominant cohorts."]
        )

    # 2 Age groups by department (stack)
    if {"age","dept_name"}.issubset(snapshot.columns) and snapshot[["age","dept_name"]].dropna().shape[0] > 0:
        tmp = snapshot.dropna(subset=["age","dept_name"]).copy()
        tmp["age_group"] = pd.cut(tmp["age"], [10,20,30,40,50,60,70], labels=["10s","20s","30s","40s","50s","60s"], right=False)
        pivot = tmp.pivot_table(index="dept_name", columns="age_group", values="employee_id", aggfunc="count", fill_value=0).reset_index()
        ycols = pivot.columns[1:]
        fig = px.bar(pivot, x="dept_name", y=ycols, barmode="stack", color_discrete_sequence=pal["seq"])
        fig.update_xaxes(tickangle=45)
        fig = style_plotly(fig, "Age Group Composition by Department")
        render_card(
            "Age Group Composition by Department",
            fig,
            description="Stacked headcount by age group for each department.",
            insights=["Detect departments with skewed demographics."],
            recommendations=["Balance hiring to reduce succession risk."]
        )

    # 3 Headcount by department
    if "dept_name" in snapshot.columns and snapshot["dept_name"].notna().any():
        dep = snapshot["dept_name"].value_counts().reset_index()
        dep.columns = ["Department","Headcount"]
        fig = px.bar(dep, x="Department", y="Headcount", color="Headcount", color_continuous_scale=pal["seq"])
        fig = style_plotly(fig, "Headcount by Department")
        render_card(
            "Headcount by Department",
            fig,
            description="Number of employees per department.",
            insights=["Highlights large and small departments."],
            recommendations=["Align hiring plans with demand."]
        )

    # 4 Top titles by headcount (Top 20)
    if "title" in snapshot.columns and snapshot["title"].notna().any():
        t = snapshot["title"].fillna("Unknown").value_counts().head(20).reset_index()
        t.columns = ["Title","Headcount"]
        fig = px.bar(t, x="Title", y="Headcount", color="Headcount", color_continuous_scale=pal["seq"])
        fig.update_xaxes(tickangle=45)
        fig = style_plotly(fig, "Top 20 Titles by Headcount")
        render_card(
            "Top 20 Titles by Headcount",
            fig,
            description="Most common job titles in the organization.",
            insights=["Shows dependency on specific roles."],
            recommendations=["Cross-train critical roles to reduce single-point risk."]
        )

    # 5 Age by department (box)
    if {"age","dept_name"}.issubset(snapshot.columns) and snapshot[["age","dept_name"]].dropna().shape[0] > 0:
        fig = px.box(snapshot.dropna(subset=["age","dept_name"]), x="dept_name", y="age", color="dept_name")
        fig.update_xaxes(tickangle=45)
        fig = style_plotly(fig, "Age by Department (Box)")
        render_card(
            "Age by Department (Box)",
            fig,
            description="Age distribution per department.",
            insights=["Wide spreads highlight heterogenous teams."],
            recommendations=["Tailor wellbeing and career programs by team profile."]
        )

    # 6 Gender overall
    gender_col = next((c for c in ["gender","sex","Gender","Sex"] if c in snapshot.columns), None)
    if gender_col and snapshot[gender_col].notna().any():
        counts = snapshot[gender_col].value_counts().reset_index()
        counts.columns = ["Gender","Count"]
        fig = px.pie(counts, names="Gender", values="Count")
        fig = style_plotly(fig, "Gender Mix (Overall)")
        render_card(
            "Gender Mix (Overall)",
            fig,
            description="Company-wide gender composition.",
            insights=["Useful to track diversity goals."],
            recommendations=["Apply unbiased sourcing and screening."]
        )

    # 7 Gender ratio by department
    if gender_col and "dept_name" in snapshot.columns and snapshot[[gender_col,"dept_name"]].dropna().shape[0] > 0:
        gdept = snapshot[[gender_col,"dept_name"]].dropna().value_counts().reset_index(name="Count")
        gdept = gdept.rename(columns={gender_col:"Gender"})
        fig = px.bar(gdept, x="dept_name", y="Count", color="Gender", barmode="stack")
        fig.update_xaxes(tickangle=45)
        fig = style_plotly(fig, "Gender Ratio by Department")
        render_card(
            "Gender Ratio by Department",
            fig,
            description="Gender composition per department.",
            insights=["Identifies skewed departments."],
            recommendations=["Set local targets and mentorship programs."]
        )

    # 8 Age vs Tenure heatmap
    if {"age","company_tenure"}.issubset(snapshot.columns) and snapshot[["age","company_tenure"]].dropna().shape[0] > 0:
        fig = px.density_heatmap(snapshot.dropna(subset=["age","company_tenure"]), x="age", y="company_tenure", nbinsx=20, nbinsy=20, color_continuous_scale=pal["seq"])
        fig = style_plotly(fig, "Age vs Tenure (Heatmap)")
        render_card(
            "Age vs Tenure (Heatmap)",
            fig,
            description="Density of employees by age and tenure.",
            insights=["Clusters show career-stage concentrations."],
            recommendations=["Design stage-specific L&D and retention programs."]
        )

# -------------------- Salaries & Compensation (8 charts) --------------------
def render_salaries():
    pal = PALETTES["salaries"]
    st.header("Salaries & Compensation")

    # prepare latest salary safely
    latest_sal = salary.copy() if {"employee_id","amount"}.issubset(salary.columns) else pd.DataFrame()
    if not latest_sal.empty:
        latest_sal = latest_per_employee(latest_sal, "from_date")
    # 1 Average salary per year
    if not salary.empty and "from_date" in salary.columns:
        s = salary.copy()
        s["from_date"] = to_dt(s["from_date"])
        s["year"] = s["from_date"].dt.year
        avg = s.groupby("year")["amount"].mean().reset_index()
        fig = px.line(avg, x="year", y="amount", markers=True)
        fig = style_plotly(fig, "Average Salary Over Time")
        render_card(
            "Average Salary Over Time",
            fig,
            description="Year-over-year average salary.",
            insights=["Shows pay growth trajectory."],
            recommendations=["Benchmark and budget merit increases accordingly."]
        )

    # 2 Top 20 salaries table
    if not salary.empty:
        top = salary.groupby("employee_id")["amount"].max().sort_values(ascending=False).head(20).reset_index()
        top.columns = ["Employee ID","Top Salary"]
        render_card(
            "Top 20 Salaries (Table)",
            table=top,
            description="Highest observed salary per employee.",
            insights=["Reveals executive bands and outliers."],
            recommendations=["Validate approvals and internal parity for top-paid employees."]
        )

    # 3 Salary histogram (latest)
    if not latest_sal.empty:
        fig = px.histogram(latest_sal, x="amount", nbins=40, color_discrete_sequence=[pal["primary"]])
        fig = style_plotly(fig, "Salary Distribution (Latest)")
        render_card(
            "Salary Distribution (Latest)",
            fig,
            description="Distribution of latest salaries.",
            insights=["Skewness or compression can be spotted."],
            recommendations=["Consider pay band adjustments where needed."]
        )

    # 4 Avg salary by department
    if "dept_name" in snapshot.columns and not latest_sal.empty:
        m = snapshot[["employee_id","dept_name"]].merge(latest_sal[["employee_id","amount"]], on="employee_id", how="left").dropna(subset=["amount"])
        g = m.groupby("dept_name")["amount"].mean().reset_index().sort_values("amount", ascending=False)
        fig = px.bar(g, x="dept_name", y="amount", color="amount", color_continuous_scale=pal["seq"])
        fig.update_xaxes(tickangle=45)
        fig = style_plotly(fig, "Average Salary by Department")
        render_card(
            "Average Salary by Department",
            fig,
            description="Mean latest pay per department.",
            insights=["Shows high-paying vs low-paying functions."],
            recommendations=["Benchmark critical roles and adjust accordingly."]
        )

    # 5 Tenure vs salary scatter
    if "company_tenure" in snapshot.columns and not latest_sal.empty:
        m = snapshot[["employee_id","company_tenure"]].merge(latest_sal[["employee_id","amount"]], on="employee_id", how="left").dropna()
        fig = px.scatter(m, x="company_tenure", y="amount", trendline="ols")
        fig = style_plotly(fig, "Tenure vs Salary")
        render_card(
            "Tenure vs Salary",
            fig,
            description="Relationship between tenure and pay.",
            insights=["Shows how pay progresses with tenure."],
            recommendations=["Define progression bands tied to tenure and performance."]
        )

    # 6 Salary growth top 10
    if not salary.empty:
        g = salary.groupby("employee_id")["amount"].agg(["min","max"]).reset_index()
        g = g[g["min"] > 0]
        g["growth_%"] = ((g["max"] - g["min"]) / g["min"]) * 100
        topg = g.sort_values("growth_%", ascending=False).head(10)
        fig = px.bar(topg, x="employee_id", y="growth_%", color="growth_%", color_continuous_scale=pal["seq"])
        fig = style_plotly(fig, "Top 10 Salary Growth %")
        render_card(
            "Top 10 Salary Growth %",
            fig,
            description="Percentage growth from earliest to latest salary.",
            insights=["Identifies fast-tracked employees or salary compression fixes."],
            recommendations=["Audit fairness and align with performance outcomes."]
        )

    # 7 Salary spread by department (strip)
    if "dept_name" in snapshot.columns and not latest_sal.empty:
        m = snapshot[["employee_id","dept_name"]].merge(latest_sal[["employee_id","amount"]], on="employee_id", how="left").dropna()
        fig = px.strip(m, x="dept_name", y="amount", color="dept_name")
        fig.update_xaxes(tickangle=45)
        fig = style_plotly(fig, "Salary Spread by Department")
        render_card(
            "Salary Spread by Department",
            fig,
            description="Point distribution of salaries per department.",
            insights=["Shows outliers and range overlap across departments."],
            recommendations=["Standardize ranges and document exceptions."]
        )

    # 8 Avg salary by title (Top 30)
    if "title" in snapshot.columns and not latest_sal.empty:
        m = snapshot[["employee_id","title"]].merge(latest_sal[["employee_id","amount"]], on="employee_id", how="left").dropna()
        g = m.groupby("title")["amount"].mean().reset_index().sort_values("amount", ascending=False).head(30)
        fig = px.bar(g, x="title", y="amount")
        fig.update_xaxes(tickangle=45)
        fig = style_plotly(fig, "Average Salary by Title (Top 30)")
        render_card(
            "Average Salary by Title (Top 30)",
            fig,
            description="Mean pay for top titles.",
            insights=["Reveals premium roles and potential pay gaps."],
            recommendations=["Perform pay-equity analysis within bands."]
        )

# -------------------- Promotions & Career Growth (7 charts) --------------------
def render_promotions():
    pal = PALETTES["promotions"]
    st.header("Promotions & Career Growth")

    if {"employee_id","title","from_date"}.issubset(title.columns) and title.shape[0] > 0:
        tdf = title.copy()
        tdf["from_date"] = to_dt(tdf["from_date"])
        tdf = tdf.sort_values(["employee_id","from_date"])
        tdf["prev_title"] = tdf.groupby("employee_id")["title"].shift()
        tdf["changed"] = (tdf["title"] != tdf["prev_title"]).astype("int")
        tdf["year"] = tdf["from_date"].dt.year
        promos = tdf.groupby("employee_id")["changed"].sum().reset_index(name="promotion_count")

        # 1 Promotions per year
        per_year = tdf[tdf["changed"]==1].groupby("year").size().reset_index(name="Promotions")
        fig = px.bar(per_year, x="year", y="Promotions", color="Promotions", color_continuous_scale=pal["seq"])
        fig = style_plotly(fig, "Promotions per Year")
        render_card(
            "Promotions per Year",
            fig,
            description="Title changes counted per year.",
            insights=["Shows waves of internal career movement."],
            recommendations=["Establish predictable promotion cadence."]
        )

        # 2 Time to first promotion (if hire_date available)
        if "hire_date" in employee.columns and employee["hire_date"].notna().any():
            first_change = tdf[tdf["changed"]==1].groupby("employee_id")["from_date"].min().reset_index().rename(columns={"from_date":"first_promo_date"})
            emp_tmp = employee[["employee_id","hire_date"]].merge(first_change, on="employee_id", how="inner")
            emp_tmp["time_to_first_promo_years"] = (to_dt(emp_tmp["first_promo_date"]) - to_dt(emp_tmp["hire_date"])).dt.days/365.25
            fig = px.histogram(emp_tmp, x="time_to_first_promo_years", nbins=30, color_discrete_sequence=[pal["primary"]])
            fig = style_plotly(fig, "Time to First Promotion (Years)")
            render_card(
                "Time to First Promotion (Years)",
                fig,
                description="Distribution of time to first title change.",
                insights=["Long waits can harm retention of high-potential employees."],
                recommendations=["Publish promotion timelines and criteria."]
            )

        # 3 Promotions by department
        if "dept_name" in snapshot.columns:
            pmap = promos.merge(snapshot[["employee_id","dept_name"]], on="employee_id", how="left")
            by_dept = pmap.groupby("dept_name")["promotion_count"].sum().reset_index().sort_values("promotion_count", ascending=False)
            fig = px.bar(by_dept, x="dept_name", y="promotion_count", color="promotion_count", color_continuous_scale=pal["seq"])
            fig.update_xaxes(tickangle=45)
            fig = style_plotly(fig, "Promotions by Department")
            render_card(
                "Promotions by Department",
                fig,
                description="Total promotions associated with current departments.",
                insights=["Shows career-progressive vs flat units."],
                recommendations=["Add internal mobility lanes in flat units."]
            )

        # 4 Multi-promotion employees (Top 20)
        top_multi = promos.sort_values("promotion_count", ascending=False).head(20)
        fig = px.bar(top_multi, x="employee_id", y="promotion_count", color="promotion_count", color_continuous_scale=pal["seq"])
        fig = style_plotly(fig, "Employees with Multiple Promotions (Top 20)")
        render_card(
            "Employees with Multiple Promotions (Top 20)",
            fig,
            description="Employees who received the most title changes.",
            insights=["High-trajectory employees identified."],
            recommendations=["Design leadership programs for high potentials."]
        )

        # 5 Promotions by gender (if gender exists)
        gcol = next((c for c in ["gender","sex","Gender","Sex"] if c in snapshot.columns), None)
        if gcol:
            mg = promos.merge(snapshot[["employee_id", gcol]], on="employee_id", how="left")
            by_g = mg.groupby(gcol)["promotion_count"].sum().reset_index().rename(columns={gcol:"Gender"})
            fig = px.bar(by_g, x="Gender", y="promotion_count", color="promotion_count", color_continuous_scale=pal["seq"])
            fig = style_plotly(fig, "Promotions by Gender")
            render_card(
                "Promotions by Gender",
                fig,
                description="Aggregated promotions by gender.",
                insights=["Can surface bias or pipeline issues."],
                recommendations=["Use calibrated promotion panels and monitor ratios."]
            )

        # 6 Career path length (titles per employee)
        path_len = title.groupby("employee_id").size().reset_index(name="title_steps")
        fig = px.histogram(path_len, x="title_steps", nbins=20, color_discrete_sequence=[pal["primary"]])
        fig = style_plotly(fig, "Career Path Length (Title Steps)")
        render_card(
            "Career Path Length (Title Steps)",
            fig,
            description="Number of title records per employee; proxy for moves.",
            insights=["Differentiates flat vs dynamic career patterns."],
            recommendations=["Enable lateral moves where vertical paths are limited."]
        )

        # 7 Promotions heatmap (department × year)
        if "dept_name" in snapshot.columns:
            mm = tdf[tdf["changed"]==1].merge(snapshot[["employee_id","dept_name"]], on="employee_id", how="left")
            heat = mm.pivot_table(index="dept_name", columns="year", values="employee_id", aggfunc="count", fill_value=0)
            if heat.shape[0] > 0 and heat.shape[1] > 0:
                fig = px.imshow(heat, aspect="auto", color_continuous_scale=pal["seq"])
                fig = style_plotly(fig, "Promotions Heatmap (Department × Year)")
                render_card(
                    "Promotions Heatmap (Department × Year)",
                    fig,
                    description="Where and when promotions happen most.",
                    insights=["Shows timing and departmental cadence of promotions."],
                    recommendations=["Smooth promotion cycles to reduce churn risk."]
                )
    else:
        st.info("Title data not available or missing required columns (employee_id, title, from_date).")

# -------------------- Retention & Turnover (7 charts) --------------------
def render_retention():
    pal = PALETTES["retention"]
    st.header("Retention & Turnover")

    # 1 Tenure distribution
    if "company_tenure" in snapshot.columns and snapshot["company_tenure"].notna().any():
        fig = px.histogram(snapshot.dropna(subset=["company_tenure"]), x="company_tenure", nbins=40, color_discrete_sequence=[pal["primary"]])
        fig = style_plotly(fig, "Tenure Distribution (Years)")
        render_card(
            "Tenure Distribution (Years)",
            fig,
            description="Distribution of employee tenure in years.",
            insights=["Shows early churn vs long-tenured employees."],
            recommendations=["Strengthen onboarding and mentorship to reduce early churn."]
        )

    # 2 Tenure by department (box)
    if {"dept_name","company_tenure"}.issubset(snapshot.columns) and snapshot[["dept_name","company_tenure"]].dropna().shape[0] > 0:
        fig = px.box(snapshot.dropna(subset=["dept_name","company_tenure"]), x="dept_name", y="company_tenure", color="dept_name")
        fig.update_xaxes(tickangle=45)
        fig = style_plotly(fig, "Tenure by Department (Box)")
        render_card(
            "Tenure by Department (Box)",
            fig,
            description="Tenure spread and medians per department.",
            insights=["Units with systematic low tenure can be flagged."],
            recommendations=["Investigate management, workload, and career options in flagged units."]
        )

    # 3 Active headcount over time (approx)
    if "hire_date" in employee.columns:
        emp_h = employee[["employee_id","hire_date","termination_date"]].copy() if {"employee_id","hire_date"}.issubset(employee.columns) else pd.DataFrame()
        if not emp_h.empty:
            emp_h["hire_year"] = to_dt(emp_h["hire_date"]).dt.year
            hires = emp_h["hire_year"].value_counts().sort_index().cumsum().reset_index()
            hires.columns = ["Year","Cumulative Hires"]
            fig = px.line(hires, x="Year", y="Cumulative Hires", markers=True)
            fig = style_plotly(fig, "Active Headcount Over Time (Approx)")
            render_card(
                "Active Headcount Over Time (Approx)",
                fig,
                description="Approximate cumulative active headcount by hire year.",
                insights=["Shows growth or contraction phases."],
                recommendations=["Adjust hiring plans to match business cycles."]
            )

    # 4 Terminations per year (if available)
    if "termination_date" in employee.columns and employee["termination_date"].notna().any():
        emp_t = employee[["employee_id","termination_date"]].copy()
        emp_t["term_year"] = to_dt(emp_t["termination_date"]).dt.year
        terms = emp_t["term_year"].dropna().value_counts().sort_index().reset_index()
        terms.columns = ["Year","Terminations"]
        fig = px.bar(terms, x="Year", y="Terminations", color="Terminations", color_continuous_scale=pal["seq"])
        fig = style_plotly(fig, "Terminations per Year")
        render_card(
            "Terminations per Year",
            fig,
            description="Annual terminations (if data available).",
            insights=["Spot spikes and correlate with org events."],
            recommendations=["Conduct exit analysis for spike years."]
        )

    # 5 Attrition rate by department (if termination exists)
    if "termination_date" in employee.columns and "dept_name" in snapshot.columns:
        active = snapshot[["employee_id","dept_name"]]
        terms = employee[["employee_id","termination_date"]].copy()
        mm = active.merge(terms, on="employee_id", how="left")
        mm["has_left"] = mm["termination_date"].notna().astype(int)
        rate = mm.groupby("dept_name")["has_left"].mean().reset_index().rename(columns={"has_left":"attrition_rate"})
        fig = px.bar(rate, x="dept_name", y="attrition_rate", color="attrition_rate", color_continuous_scale=pal["seq"])
        fig.update_xaxes(tickangle=45)
        fig = style_plotly(fig, "Attrition Rate by Department")
        render_card(
            "Attrition Rate by Department",
            fig,
            description="Share of employees with termination records per department.",
            insights=["Identify at-risk teams."],
            recommendations=["Run stay interviews and manager coaching in flagged teams."]
        )

    # 6 Tenure vs salary heatmap
    if {"employee_id","amount"}.issubset(salary.columns) and "company_tenure" in snapshot.columns:
        sal_latest = latest_per_employee(salary, "from_date")
        mm = snapshot[["employee_id","company_tenure"]].merge(sal_latest[["employee_id","amount"]], on="employee_id", how="left").dropna()
        if mm.shape[0] > 0:
            fig = px.density_heatmap(mm, x="company_tenure", y="amount", nbinsx=25, nbinsy=25, color_continuous_scale=pal["seq"])
            fig = style_plotly(fig, "Tenure vs Salary (Heatmap)")
            render_card(
                "Tenure vs Salary (Heatmap)",
                fig,
                description="Joint distribution of tenure and pay.",
                insights=["Shows pay plateaus or rapid increases with tenure."],
                recommendations=["Design step increases and promotion guidelines to avoid plateaus."]
            )

    # 7 Department moves per employee (transfer proxy)
    if "employee_id" in department_employee.columns:
        counts = department_employee.groupby("employee_id").size().reset_index(name="dept_moves")
        moves = counts["dept_moves"].value_counts().reset_index()
        moves.columns = ["Moves","Employees"]
        fig = px.bar(moves, x="Moves", y="Employees", color="Employees", color_continuous_scale=pal["seq"])
        fig = style_plotly(fig, "Department Moves per Employee")
        render_card(
            "Department Moves per Employee",
            fig,
            description="Proxy for internal mobility frequency.",
            insights=["High mobility may indicate healthy internal movement."],
            recommendations=["Promote internal vacancies and simplify transfer policies."]
        )

# -------------------- Page routing & bottom nav --------------------
# show current page content
current_page = page  # already synced with session_state

if current_page == "About":
    render_about()
elif current_page == "Demographics":
    render_demographics()
elif current_page == "Salaries":
    render_salaries()
elif current_page == "Promotions":
    render_promotions()
elif current_page == "Retention":
    render_retention()

# Bottom navigation buttons
cols = st.columns([1,1,1,1,1])
if cols[0].button("⟵ Previous", key="prev"):
    st.session_state.page_index = max(0, st.session_state.page_index - 1)
    st.experimental_rerun()
if cols[1].button("Next ⟶", key="next"):
    st.session_state.page_index = min(len(PAGES)-1, st.session_state.page_index + 1)
    st.experimental_rerun()
# quick jump buttons
if cols[2].button("Go to About", key="about"):
    st.session_state.page_index = 0
    st.experimental_rerun()
if cols[3].button("Go to Demographics", key="demobtn"):
    st.session_state.page_index = 1
    st.experimental_rerun()
if cols[4].button("Go to Salaries", key="paybtn"):
    st.session_state.page_index = 2
    st.experimental_rerun()

# Synchronize sidebar radio with session_state index after rerun
st.session_state.page_index = st.session_state.page_index
