# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Try import statsmodels (optional, used by plotly trendline="ols")
try:
    import statsmodels.api as sm  # noqa: F401
    HAS_STATSMODELS = True
except Exception:
    HAS_STATSMODELS = False

# ---------------- Page config ----------------
st.set_page_config(page_title="HR Analytics Dashboard", layout="wide")

# ---------------- Sidebar settings ----------------
with st.sidebar:
    st.header("Settings")
    DARK_MODE = st.toggle("Dark mode", value=True)
    st.markdown("Use sidebar to navigate pages and change theme.")

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

st.markdown(
    f"""
<style>
    .stApp {{ background:{BG_COLOR}; color:{TEXT_COLOR}; }}
    .card {{ background:{PANEL_COLOR}; padding:16px; border-radius:12px; margin-bottom:12px; }}
    h1,h2,h3 {{ color:{TEXT_COLOR} !important; }}
    .muted {{ opacity:0.85; font-size:0.95rem; }}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------- Helpers ----------------
def to_dt(s):
    return pd.to_datetime(s, errors="coerce")

def load_csv_safe(path):
    try:
        return pd.read_csv(path)
    except Exception:
        # return empty dataframe with no columns
        return pd.DataFrame()

def ensure_columns(df, cols):
    """Make sure df contains cols; put NaT for date-like names else NaN."""
    for c in cols:
        if c not in df.columns:
            if "date" in c or "hire" in c or "termination" in c or "from_date" in c or "to_date" in c:
                df[c] = pd.NaT
            else:
                df[c] = np.nan
    return df

def latest_per_employee(df, date_col):
    """Return last record per employee based on date_col; safe when date_col missing."""
    if df.empty or "employee_id" not in df.columns:
        return pd.DataFrame(columns=df.columns)
    df = df.copy()
    if date_col not in df.columns:
        df["_art_date"] = pd.Timestamp("1970-01-01")
        date_col = "_art_date"
    df[date_col] = to_dt(df[date_col])
    df = df.sort_values(["employee_id", date_col])
    return df.groupby("employee_id", as_index=False).tail(1)

def style_plotly(fig, title=None, height=None):
    try:
        fig.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        if title:
            fig.update_layout(title=dict(text=title, x=0.02, xanchor="left"))
        if height:
            fig.update_layout(height=height)
    except Exception:
        pass
    return fig

def render_card(title, fig=None, table=None, description="", insights=None, recs=None):
    st.markdown(f"<div class='card'><h3>{title}</h3>", unsafe_allow_html=True)
    if fig is not None:
        try:
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Plot error: {e}")
    if table is not None:
        try:
            st.dataframe(table, use_container_width=True)
        except Exception:
            pass
    if description:
        st.markdown(f"**Description:** {description}")
    if insights:
        st.markdown("**Insights:**")
        for it in insights:
            st.markdown(f"- {it}")
    if recs:
        st.markdown("**Recommendations:**")
        for r in recs:
            st.markdown(f"- {r}")
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------- Load data ----------------
salary = load_csv_safe("salary.csv")
employee = load_csv_safe("employee.csv")
current_snapshot = load_csv_safe("current_employee_snapshot.csv")
department = load_csv_safe("department.csv")
department_employee = load_csv_safe("department_employee.csv")
title = load_csv_safe("title.csv")

# Ensure columns to avoid KeyError
employee = ensure_columns(employee, ["id", "employee_id", "birth_date", "hire_date", "termination_date", "gender"])
salary = ensure_columns(salary, ["employee_id", "amount", "from_date", "to_date"])
current_snapshot = ensure_columns(current_snapshot, ["employee_id", "dept_name", "title", "salary_amount", "age", "company_tenure"])
department_employee = ensure_columns(department_employee, ["employee_id", "dept_id", "from_date", "to_date"])
department = ensure_columns(department, ["dept_id", "dept_name"])
title = ensure_columns(title, ["employee_id", "title", "from_date", "to_date"])

# Normalize employee id
if "id" in employee.columns and "employee_id" not in employee.columns:
    employee = employee.rename(columns={"id": "employee_id"})

# Compute derived columns in employee if missing
if "birth_date" in employee.columns:
    employee["birth_date"] = to_dt(employee["birth_date"])
    employee["age"] = employee.get("age", (datetime.now().year - employee["birth_date"].dt.year).astype("float"))
else:
    employee["age"] = employee.get("age", np.nan)

if "hire_date" in employee.columns:
    employee["hire_date"] = to_dt(employee["hire_date"])
    employee["company_tenure"] = employee.get("company_tenure", (pd.Timestamp.today() - employee["hire_date"]).dt.days / 365.25)
else:
    employee["company_tenure"] = employee.get("company_tenure", np.nan)

# Build unified snapshot
# latest dept
if {"employee_id", "dept_id"}.issubset(department_employee.columns) and {"dept_id", "dept_name"}.issubset(department.columns):
    dept_merged = department_employee.merge(department, on="dept_id", how="left")
    dept_latest = latest_per_employee(dept_merged, "to_date" if "to_date" in department_employee.columns else "from_date")
    dept_latest = dept_latest[["employee_id", "dept_name"]] if "dept_name" in dept_latest.columns else pd.DataFrame(columns=["employee_id", "dept_name"])
else:
    dept_latest = current_snapshot[["employee_id", "dept_name"]].drop_duplicates() if {"employee_id", "dept_name"}.issubset(current_snapshot.columns) else pd.DataFrame(columns=["employee_id", "dept_name"])

# latest title
if {"employee_id", "title"}.issubset(title.columns):
    title_latest = latest_per_employee(title, "to_date" if "to_date" in title.columns else "from_date")
    title_latest = title_latest[["employee_id", "title"]] if "title" in title_latest.columns else pd.DataFrame(columns=["employee_id", "title"])
else:
    title_latest = current_snapshot[["employee_id", "title"]].drop_duplicates() if {"employee_id", "title"}.issubset(current_snapshot.columns) else pd.DataFrame(columns=["employee_id", "title"])

# latest salary
if {"employee_id", "amount"}.issubset(salary.columns):
    sal_latest = latest_per_employee(salary, "from_date" if "from_date" in salary.columns else "to_date")
    sal_latest = sal_latest[["employee_id", "amount"]].rename(columns={"amount": "latest_salary"}) if "amount" in sal_latest.columns else pd.DataFrame(columns=["employee_id", "latest_salary"])
else:
    sal_latest = pd.DataFrame(columns=["employee_id", "latest_salary"])

# base employees
if "employee_id" in employee.columns:
    base_emp = employee.copy()
else:
    base_emp = current_snapshot[["employee_id"]].drop_duplicates() if "employee_id" in current_snapshot.columns else pd.DataFrame(columns=["employee_id"])

# merge snapshot
snapshot = base_emp.merge(dept_latest, on="employee_id", how="left") \
                   .merge(title_latest, on="employee_id", how="left") \
                   .merge(sal_latest, on="employee_id", how="left")

# bring extras from current_snapshot
if "employee_id" in current_snapshot.columns:
    extras = [c for c in current_snapshot.columns if c not in snapshot.columns and c != "employee_id"]
    if extras:
        snapshot = snapshot.merge(current_snapshot[["employee_id"] + extras], on="employee_id", how="left")

for c in ["dept_name", "title", "company_tenure", "age", "latest_salary", "gender"]:
    if c not in snapshot.columns:
        snapshot[c] = np.nan

# ---------------- Pages and navigation ----------------
PAGES = ["About", "Demographics", "Salaries", "Promotions", "Retention"]
if "page" not in st.session_state:
    st.session_state.page = "About"

page = st.sidebar.radio("Page", PAGES, index=PAGES.index(st.session_state.page))
st.session_state.page = page

st.title("HR Analytics Dashboard")
st.markdown("30+ charts across Demographics, Salaries, Promotions, and Retention. Each chart contains Description → Insights → Recommendations.")
st.markdown("---")

# ---------------- About Page ----------------
def page_about():
    st.header("About")
    st.markdown(
        """
**Purpose**  
This dashboard aggregates HR data to provide insights on workforce composition, compensation, promotions, and retention.

**Features**
- 30+ interactive charts
- Light / Dark theme
- Defensive handling of missing columns
- Descriptions, insights and recommendations for each visualization

**Data (recommended)**
- employee.csv (id/employee_id, birth_date, hire_date, termination_date, gender)
- salary.csv (employee_id, amount, from_date, to_date)
- title.csv (employee_id, title, from_date, to_date)
- department_employee.csv + department.csv
- current_employee_snapshot.csv (optional)

**How to use**
1. Put CSV files in the same folder as app.py.
2. Use sidebar to switch pages and theme.
3. Use bottom navigation buttons for quick jumps.
        """
    )

# ---------------- Demographics ----------------
def page_demographics():
    pal = PALETTES["demographics"]
    st.header("Demographics")

    # 1 Age histogram
    if snapshot["age"].notna().any():
        df = snapshot.dropna(subset=["age"])
        fig = px.histogram(df, x="age", nbins=40, color_discrete_sequence=[pal["primary"]])
        fig = style_plotly(fig, "Age Distribution")
        render_card(
            "Age Distribution",
            fig,
            description="Histogram of employee ages.",
            insights=["Shows dominant cohorts and outliers."],
            recs=["Tailor learning & benefits to dominant cohorts."]
        )

    # 2 Age group composition by dept
    if snapshot[["age", "dept_name"]].dropna().shape[0] > 0:
        tmp = snapshot.dropna(subset=["age", "dept_name"]).copy()
        tmp["age_group"] = pd.cut(tmp["age"], [10,20,30,40,50,60,70], labels=["10s","20s","30s","40s","50s","60s"], right=False)
        pivot = tmp.pivot_table(index="dept_name", columns="age_group", values="employee_id", aggfunc="count", fill_value=0).reset_index()
        if pivot.shape[1] > 1:
            ycols = pivot.columns[1:]
            fig = px.bar(pivot, x="dept_name", y=ycols, barmode="stack", color_discrete_sequence=pal["seq"])
            fig.update_xaxes(tickangle=45)
            fig = style_plotly(fig, "Age Group Composition by Department")
            render_card(
                "Age Group Composition by Department",
                fig,
                description="Stacked headcount by age group for each department.",
                insights=["Detect skewed department demographics."],
                recs=["Balance hiring to reduce succession risk."]
            )

    # 3 Headcount by dept
    if snapshot["dept_name"].notna().any():
        dep = snapshot["dept_name"].value_counts().reset_index()
        dep.columns = ["Department", "Headcount"]
        fig = px.bar(dep, x="Department", y="Headcount", color="Headcount", color_continuous_scale=pal["seq"])
        fig = style_plotly(fig, "Headcount by Department")
        render_card(
            "Headcount by Department",
            fig,
            description="Number of employees per department.",
            insights=["Highlights large and small departments."],
            recs=["Align hiring with demand."]
        )

    # 4 Top titles by headcount
    if snapshot["title"].notna().any():
        t = snapshot["title"].fillna("Unknown").value_counts().head(20).reset_index()
        t.columns = ["Title", "Headcount"]
        fig = px.bar(t, x="Title", y="Headcount", color="Headcount", color_continuous_scale=pal["seq"])
        fig.update_xaxes(tickangle=45)
        fig = style_plotly(fig, "Top Titles by Headcount")
        render_card(
            "Top Titles by Headcount (Top 20)",
            fig,
            description="Most common titles.",
            insights=["Shows concentration of roles."],
            recs=["Cross-train critical roles."]
        )

    # 5 Age by department box
    if snapshot[["age","dept_name"]].dropna().shape[0] > 0:
        fig = px.box(snapshot.dropna(subset=["age","dept_name"]), x="dept_name", y="age", color="dept_name")
        fig.update_xaxes(tickangle=45)
        fig = style_plotly(fig, "Age by Department (Box)")
        render_card(
            "Age by Department (Box)",
            fig,
            description="Spread & median age per department.",
            insights=["Wide spreads indicate heterogeneous teams."],
            recs=["Customize programs per team profile."]
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
            insights=["Useful for diversity tracking."],
            recs=["Apply unbiased sourcing & screening."]
        )

    # 7 Gender ratio by department
    if gender_col and snapshot[["dept_name", gender_col]].dropna().shape[0] > 0:
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
            recs=["Set mentorship & hiring goals."]
        )

    # 8 Age vs Tenure heatmap
    if snapshot[["age","company_tenure"]].dropna().shape[0] > 0:
        fig = px.density_heatmap(snapshot.dropna(subset=["age","company_tenure"]), x="age", y="company_tenure", nbinsx=20, nbinsy=20, color_continuous_scale=pal["seq"])
        fig = style_plotly(fig, "Age vs Tenure (Heatmap)")
        render_card(
            "Age vs Tenure (Heatmap)",
            fig,
            description="Density of employees by age and tenure.",
            insights=["Clusters show career stage concentrations."],
            recs=["Design stage-specific L&D & retention programs."]
        )

# ---------------- Salaries ----------------
def page_salaries():
    pal = PALETTES["salaries"]
    st.header("Salaries & Compensation")

    latest_sal = pd.DataFrame()
    if {"employee_id","amount"}.issubset(salary.columns):
        latest_sal = latest_per_employee(salary, "from_date" if "from_date" in salary.columns else "to_date")

    # 1 Average salary per year
    if {"employee_id","amount","from_date"}.issubset(salary.columns) and salary.shape[0] > 0:
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
            recs=["Benchmark and budget merit increases."]
        )

    # 2 Top salaries (table)
    if {"employee_id","amount"}.issubset(salary.columns) and salary.shape[0] > 0:
        top = salary.groupby("employee_id")["amount"].max().sort_values(ascending=False).head(20).reset_index()
        top.columns = ["Employee ID","Top Salary"]
        render_card(
            "Top 20 Salaries (Table)",
            table=top,
            description="Highest observed salary per employee.",
            insights=["Executive bands and outliers."],
            recs=["Validate approvals and parity."]
        )

    # 3 Salary histogram (latest)
    if latest_sal.shape[0] > 0:
        fig = px.histogram(latest_sal, x="amount", nbins=40, color_discrete_sequence=[pal["primary"]])
        fig = style_plotly(fig, "Salary Distribution (Latest)")
        render_card(
            "Salary Distribution (Latest)",
            fig,
            description="Distribution of latest salaries.",
            insights=["Spot skewness and compression."],
            recs=["Consider band adjustments."]
        )

    # 4 Average salary by department
    if latest_sal.shape[0] > 0 and snapshot["dept_name"].notna().any():
        m = snapshot[["employee_id","dept_name"]].merge(latest_sal[["employee_id","amount"]], on="employee_id", how="left").dropna(subset=["amount"])
        if m.shape[0] > 0:
            g = m.groupby("dept_name")["amount"].mean().reset_index().sort_values("amount", ascending=False)
            fig = px.bar(g, x="dept_name", y="amount", color="amount", color_continuous_scale=pal["seq"])
            fig.update_xaxes(tickangle=45)
            fig = style_plotly(fig, "Average Salary by Department")
            render_card(
                "Average Salary by Department",
                fig,
                description="Mean pay per department.",
                insights=["Shows high-paying functions."],
                recs=["Benchmark critical roles."]
            )

    # 5 Tenure vs salary scatter (trendline optional)
    if latest_sal.shape[0] > 0 and snapshot["company_tenure"].notna().any():
        m = snapshot[["employee_id","company_tenure"]].merge(latest_sal[["employee_id","amount"]], on="employee_id", how="left").dropna()
        try:
            if HAS_STATSMODELS:
                fig = px.scatter(m, x="company_tenure", y="amount", trendline="ols")
            else:
                fig = px.scatter(m, x="company_tenure", y="amount")
            fig = style_plotly(fig, "Tenure vs Salary")
            render_card(
                "Tenure vs Salary",
                fig,
                description="Relationship between tenure and pay (trendline only if statsmodels is installed).",
                insights=["Reveals how pay progresses with tenure."],
                recs=["Define progression bands tied to tenure & performance."]
            )
        except Exception as e:
            st.error(f"Unable to render Tenure vs Salary: {e}")

    # 6 Salary growth top 10 %
    if {"employee_id","amount"}.issubset(salary.columns) and salary.shape[0] > 0:
        g = salary.groupby("employee_id")["amount"].agg(["min","max"]).reset_index()
        g = g[g["min"] > 0]
        if g.shape[0] > 0:
            g["growth_%"] = ((g["max"] - g["min"]) / g["min"]) * 100
            topg = g.sort_values("growth_%", ascending=False).head(10)
            fig = px.bar(topg, x="employee_id", y="growth_%", color="growth_%", color_continuous_scale=pal["seq"])
            fig = style_plotly(fig, "Top 10 Salary Growth %")
            render_card(
                "Top 10 Salary Growth %",
                fig,
                description="Percentage growth from earliest to latest salary.",
                insights=["Identifies fast-trackers or compression fixes."],
                recs=["Audit fairness and align performance."]
            )

    # 7 Salary spread by department
    if latest_sal.shape[0] > 0 and snapshot["dept_name"].notna().any():
        m = snapshot[["employee_id","dept_name"]].merge(latest_sal[["employee_id","amount"]], on="employee_id", how="left").dropna()
        if m.shape[0] > 0:
            fig = px.strip(m, x="dept_name", y="amount", color="dept_name")
            fig.update_xaxes(tickangle=45)
            fig = style_plotly(fig, "Salary Spread by Department")
            render_card(
                "Salary Spread by Department",
                fig,
                description="Point distribution of salaries per department.",
                insights=["Shows outliers and band overlaps."],
                recs=["Standardize ranges and document exceptions."]
            )

    # 8 Avg salary by title (top 30)
    if latest_sal.shape[0] > 0 and snapshot["title"].notna().any():
        m = snapshot[["employee_id","title"]].merge(latest_sal[["employee_id","amount"]], on="employee_id", how="left").dropna()
        if m.shape[0] > 0:
            g = m.groupby("title")["amount"].mean().reset_index().sort_values("amount", ascending=False).head(30)
            fig = px.bar(g, x="title", y="amount")
            fig.update_xaxes(tickangle=45)
            fig = style_plotly(fig, "Average Salary by Title (Top 30)")
            render_card(
                "Average Salary by Title (Top 30)",
                fig,
                description="Mean pay for common titles.",
                insights=["Shows premium roles and pay gaps."],
                recs=["Run pay-equity analysis."]
            )

# ---------------- Promotions ----------------
def page_promotions():
    pal = PALETTES["promotions"]
    st.header("Promotions & Career Growth")

    if {"employee_id","title","from_date"}.issubset(title.columns) and title.shape[0] > 0:
        tdf = title.copy()
        tdf["from_date"] = to_dt(tdf["from_date"])
        tdf = tdf.sort_values(["employee_id","from_date"])
        tdf["prev_title"] = tdf.groupby("employee_id")["title"].shift()
        tdf["changed"] = (tdf["title"] != tdf["prev_title"]).astype(int)
        tdf["year"] = tdf["from_date"].dt.year
        promos = tdf.groupby("employee_id")["changed"].sum().reset_index(name="promotion_count")

        # 1 Promotions per year
        per_year = tdf[tdf["changed"]==1].groupby("year").size().reset_index(name="Promotions")
        if per_year.shape[0] > 0:
            fig = px.bar(per_year, x="year", y="Promotions", color="Promotions", color_continuous_scale=pal["seq"])
            fig = style_plotly(fig, "Promotions per Year")
            render_card(
                "Promotions per Year",
                fig,
                description="Title changes counted per year.",
                insights=["Shows waves of internal career movement."],
                recs=["Establish predictable promotion cadence."]
            )

        # 2 Time to first promotion
        if "hire_date" in employee.columns and employee["hire_date"].notna().any():
            first_change = tdf[tdf["changed"]==1].groupby("employee_id")["from_date"].min().reset_index().rename(columns={"from_date":"first_promo_date"})
            emp_tmp = employee[["employee_id","hire_date"]].merge(first_change, on="employee_id", how="inner")
            emp_tmp["time_to_first_promo_years"] = (to_dt(emp_tmp["first_promo_date"]) - to_dt(emp_tmp["hire_date"])).dt.days/365.25
            if emp_tmp.shape[0] > 0:
                fig = px.histogram(emp_tmp, x="time_to_first_promo_years", nbins=30, color_discrete_sequence=[pal["primary"]])
                fig = style_plotly(fig, "Time to First Promotion (Years)")
                render_card(
                    "Time to First Promotion (Years)",
                    fig,
                    description="Distribution of time to first promotion.",
                    insights=["Long waits may harm retention of high potentials."],
                    recs=["Publish timelines & criteria for promotion."]
                )

        # 3 Promotions by department
        if snapshot["dept_name"].notna().any():
            pmap = promos.merge(snapshot[["employee_id","dept_name"]], on="employee_id", how="left")
            by_dept = pmap.groupby("dept_name")["promotion_count"].sum().reset_index().sort_values("promotion_count", ascending=False)
            if by_dept.shape[0] > 0:
                fig = px.bar(by_dept, x="dept_name", y="promotion_count", color="promotion_count", color_continuous_scale=pal["seq"])
                fig.update_xaxes(tickangle=45)
                fig = style_plotly(fig, "Promotions by Department")
                render_card(
                    "Promotions by Department",
                    fig,
                    description="Total promotions mapped to current departments.",
                    insights=["Shows career-progressive vs flat units."],
                    recs=["Create internal mobility lanes in flat units."]
                )

        # 4 Multi-promotion employees (Top 20)
        top_multi = promos.sort_values("promotion_count", ascending=False).head(20)
        if top_multi.shape[0] > 0:
            fig = px.bar(top_multi, x="employee_id", y="promotion_count", color="promotion_count", color_continuous_scale=pal["seq"])
            fig = style_plotly(fig, "Employees with Multiple Promotions (Top 20)")
            render_card(
                "Employees with Multiple Promotions (Top 20)",
                fig,
                description="Employees with the most title changes.",
                insights=["High-trajectory talent clusters."],
                recs=["Design leadership programs for high potentials."]
            )

        # 5 Promotions by gender
        gender_col = next((c for c in ["gender","sex","Gender","Sex"] if c in snapshot.columns), None)
        if gender_col:
            mg = promos.merge(snapshot[["employee_id", gender_col]], on="employee_id", how="left")
            by_g = mg.groupby(gender_col)["promotion_count"].sum().reset_index().rename(columns={gender_col:"Gender"})
            if by_g.shape[0] > 0:
                fig = px.bar(by_g, x="Gender", y="promotion_count", color="promotion_count", color_continuous_scale=pal["seq"])
                fig = style_plotly(fig, "Promotions by Gender")
                render_card(
                    "Promotions by Gender",
                    fig,
                    description="Aggregated promotions by gender.",
                    insights=["Can surface bias or pipeline issues."],
                    recs=["Use calibrated promotion panels and monitor ratios."]
                )

        # 6 Career path length
        path_len = title.groupby("employee_id").size().reset_index(name="title_steps")
        if path_len.shape[0] > 0:
            fig = px.histogram(path_len, x="title_steps", nbins=20, color_discrete_sequence=[pal["primary"]])
            fig = style_plotly(fig, "Career Path Length")
            render_card(
                "Career Path Length (Title Steps)",
                fig,
                description="Number of title records per employee.",
                insights=["Differentiates flat vs dynamic career patterns."],
                recs=["Enable lateral moves where vertical paths are limited."]
            )

        # 7 Promotions heatmap (dept x year)
        if snapshot["dept_name"].notna().any():
            mm = tdf[tdf["changed"]==1].merge(snapshot[["employee_id","dept_name"]], on="employee_id", how="left")
            heat = mm.pivot_table(index="dept_name", columns="year", values="employee_id", aggfunc="count", fill_value=0)
            if heat.shape[0] > 0 and heat.shape[1] > 0:
                fig = px.imshow(heat, aspect="auto", color_continuous_scale=pal["seq"])
                fig = style_plotly(fig, "Promotions Heatmap (Dept × Year)")
                render_card(
                    "Promotions Heatmap (Dept × Year)",
                    fig,
                    description="Where and when promotions occur.",
                    insights=["Shows timing and cadence."],
                    recs=["Smooth cycles to reduce churn risk."]
                )
    else:
        st.info("Title data not available or missing required columns (employee_id, title, from_date).")

# ---------------- Retention ----------------
def page_retention():
    pal = PALETTES["retention"]
    st.header("Retention & Turnover")

    # 1 Tenure distribution
    if snapshot["company_tenure"].notna().any():
        fig = px.histogram(snapshot.dropna(subset=["company_tenure"]), x="company_tenure", nbins=40, color_discrete_sequence=[pal["primary"]])
        fig = style_plotly(fig, "Tenure Distribution (Years)")
        render_card(
            "Tenure Distribution (Years)",
            fig,
            description="Distribution of employee tenure.",
            insights=["Shows early churn vs long-tenured employees."],
            recs=["Strengthen onboarding & mentorship."]
        )

    # 2 Tenure by department (box)
    if snapshot[["dept_name","company_tenure"]].dropna().shape[0] > 0:
        fig = px.box(snapshot.dropna(subset=["dept_name","company_tenure"]), x="dept_name", y="company_tenure", color="dept_name")
        fig.update_xaxes(tickangle=45)
        fig = style_plotly(fig, "Tenure by Department (Box)")
        render_card(
            "Tenure by Department (Box)",
            fig,
            description="Tenure spread & medians per department.",
            insights=["Flag units with low tenure."],
            recs=["Investigate leadership, workload & growth."]
        )

    # 3 Active headcount (approx)
    if "hire_date" in employee.columns and employee["hire_date"].notna().any():
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
                description="Approximate cumulative headcount by hire year.",
                insights=["Shows growth phases."],
                recs=["Align hiring with business cycles."]
            )

    # 4 Terminations per year
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
            description="Annual terminations (if recorded).",
            insights=["Spot spikes and correlate with events."],
            recs=["Perform exit analysis for spikes."]
        )

    # 5 Attrition rate by department (approx)
    if "termination_date" in employee.columns and snapshot["dept_name"].notna().any():
        active = snapshot[["employee_id","dept_name"]]
        terms = employee[["employee_id","termination_date"]].copy()
        mm = active.merge(terms, on="employee_id", how="left")
        mm["has_left"] = mm["termination_date"].notna().astype(int)
        rate = mm.groupby("dept_name")["has_left"].mean().reset_index().rename(columns={"has_left":"attrition_rate"})
        if rate.shape[0] > 0:
            fig = px.bar(rate, x="dept_name", y="attrition_rate", color="attrition_rate", color_continuous_scale=pal["seq"])
            fig.update_xaxes(tickangle=45)
            fig = style_plotly(fig, "Attrition Rate by Department")
            render_card(
                "Attrition Rate by Department",
                fig,
                description="Share of employees with termination records.",
                insights=["Flag at-risk teams."],
                recs=["Run stay interviews and manager coaching."]
            )

    # 6 Tenure vs salary heatmap (joint)
    if {"employee_id","amount"}.issubset(salary.columns) and snapshot["company_tenure"].notna().any():
        sal_latest = latest_per_employee(salary, "from_date")
        mm = snapshot[["employee_id","company_tenure"]].merge(sal_latest[["employee_id","amount"]], on="employee_id", how="left").dropna()
        if mm.shape[0] > 0:
            fig = px.density_heatmap(mm, x="company_tenure", y="amount", nbinsx=25, nbinsy=25, color_continuous_scale=pal["seq"])
            fig = style_plotly(fig, "Tenure vs Salary (Heatmap)")
            render_card(
                "Tenure vs Salary (Heatmap)",
                fig,
                description="Joint distribution of tenure and pay.",
                insights=["Shows pay plateaus or steep increases."],
                recs=["Define step increases and promotion guidelines."]
            )

    # 7 Department moves per employee (proxy for internal mobility)
    if "employee_id" in department_employee.columns:
        counts = department_employee.groupby("employee_id").size().reset_index(name="dept_moves")
        moves = counts["dept_moves"].value_counts().reset_index()
        moves.columns = ["Moves","Employees"]
        if moves.shape[0] > 0:
            fig = px.bar(moves, x="Moves", y="Employees", color="Employees", color_continuous_scale=pal["seq"])
            fig = style_plotly(fig, "Department Moves per Employee")
            render_card(
                "Department Moves per Employee",
                fig,
                description="Frequency of department records per employee.",
                insights=["Proxy for internal mobility."],
                recs=["Promote internal vacancies and simplify transfers."]
            )

# ---------------- Router ----------------
if st.session_state.page == "About":
    page_about()
elif st.session_state.page == "Demographics":
    page_demographics()
elif st.session_state.page == "Salaries":
    page_salaries()
elif st.session_state.page == "Promotions":
    page_promotions()
elif st.session_state.page == "Retention":
    page_retention()
else:
    page_about()

# ---------------- Bottom navigation ----------------
cols = st.columns([1,1,1,1,1])
prev_clicked = cols[0].button("⟵ Previous")
next_clicked = cols[1].button("Next ⟶")
if cols[2].button("Go to About"):
    st.session_state.page = "About"
    if hasattr(st, "experimental_rerun"):
        try:
            st.experimental_rerun()
        except Exception:
            pass
if cols[3].button("Go to Demographics"):
    st.session_state.page = "Demographics"
    if hasattr(st, "experimental_rerun"):
        try:
            st.experimental_rerun()
        except Exception:
            pass
if cols[4].button("Go to Salaries"):
    st.session_state.page = "Salaries"
    if hasattr(st, "experimental_rerun"):
        try:
            st.experimental_rerun()
        except Exception:
            pass

if prev_clicked:
    idx = PAGES.index(st.session_state.page)
    st.session_state.page = PAGES[max(0, idx-1)]
    if hasattr(st, "experimental_rerun"):
        try:
            st.experimental_rerun()
        except Exception:
            pass

if next_clicked:
    idx = PAGES.index(st.session_state.page)
    st.session_state.page = PAGES[min(len(PAGES)-1, idx+1)]
    if hasattr(st, "experimental_rerun"):
        try:
            st.experimental_rerun()
        except Exception:
            pass

# keep sidebar radio in sync after possible rerun changes
st.experimental_set_query_params(page=st.session_state.page)
