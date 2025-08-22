# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ---------------- Page config ----------------
st.set_page_config(page_title="HR Analytics Dashboard", layout="wide")

# ---------------- Sidebar: Theme + Nav ----------------
with st.sidebar:
    st.header("Settings")
    dark_mode = st.checkbox("Dark Mode", value=True)
    st.markdown("---")
    st.header("Navigation")
    page = st.radio("Go to", ("Overview", "Demographics", "Salaries", "Turnover & Tenure", "Promotions & Performance"))

# ---------------- Theme variables ----------------
PLOTLY_TEMPLATE = "plotly_dark" if dark_mode else "plotly_white"
TEXT_COLOR = "#e5e7eb" if dark_mode else "#0f172a"
BG_COLOR = "#0b1021" if dark_mode else "#ffffff"
PANEL_COLOR = "#111827" if dark_mode else "#f8fafc"

PALETTES = {
    "demographics": {"seq": px.colors.sequential.Blues, "primary": "#0284c7"},
    "salaries": {"seq": px.colors.sequential.Greens, "primary": "#16a34a"},
    "turnover": {"seq": px.colors.sequential.OrRd, "primary": "#f97316"},
    "promotions": {"seq": px.colors.sequential.Purples, "primary": "#7c3aed"},
    "overview": {"seq": px.colors.sequential.Viridis, "primary": "#6366f1"},
}

st.markdown(
    f"""
    <style>
      .stApp {{ background:{BG_COLOR}; color:{TEXT_COLOR}; }}
      .card {{ background:{PANEL_COLOR}; border-radius:12px; padding:12px; margin-bottom:12px; }}
      .muted {{ color: #94a3b8; }}
      h1,h2,h3,h4,h5,h6 {{ color:{TEXT_COLOR} !important; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------- Helpers ----------------
def to_dt(s):
    return pd.to_datetime(s, errors="coerce")

@st.cache_data
def load_csv_safe(path):
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

@st.cache_data
def load_all():
    salary = load_csv_safe("salary.csv")
    employee = load_csv_safe("employee.csv")
    snapshot = load_csv_safe("current_employee_snapshot.csv")
    department = load_csv_safe("department.csv")
    dept_emp = load_csv_safe("department_employee.csv")
    title = load_csv_safe("title.csv")
    # normalize some column names if common variants exist
    if "salary" in salary.columns and "amount" not in salary.columns:
        salary = salary.rename(columns={"salary":"amount"})
    if "id" in employee.columns and "employee_id" not in employee.columns:
        employee = employee.rename(columns={"id":"employee_id"})
    return salary, employee, snapshot, department, dept_emp, title

def latest_per_employee(df, date_col):
    if df is None or df.empty or "employee_id" not in df.columns:
        return pd.DataFrame()
    d = df.copy()
    if date_col not in d.columns:
        d["_tmp_date"] = pd.Timestamp("1970-01-01")
        date_col = "_tmp_date"
    d[date_col] = to_dt(d[date_col])
    d = d.sort_values(["employee_id", date_col])
    return d.groupby("employee_id", as_index=False).tail(1)

def style_layout(fig, title=None, height=None):
    try:
        fig.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        fig.update_traces(marker_line_width=0)
        if title:
            fig.update_layout(title=dict(text=title, x=0.02, xanchor="left"))
        if height:
            fig.update_layout(height=height)
    except Exception:
        pass
    return fig

def render_card(title, fig=None, table=None, description=None, insights=None, recs=None):
    st.markdown(f"<div class='card'><h3>{title}</h3>", unsafe_allow_html=True)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    if table is not None:
        st.dataframe(table, use_container_width=True)
    if description:
        st.markdown(f"**Description:** {description}")
    if insights:
        st.markdown("**Insights:**")
        for i in insights:
            st.markdown(f"- {i}")
    if recs:
        st.markdown("**Recommendations:**")
        for r in recs:
            st.markdown(f"- {r}")
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------- Load data ----------------
salary, employee, snapshot, department, dept_emp, title = load_all()

# ensure common columns exist in snapshot
for col in ["dept_name","title","company_tenure","age","latest_salary"]:
    if col not in snapshot.columns:
        snapshot[col] = np.nan

# compute simple snapshot merges (safe)
if "employee_id" in employee.columns:
    base_emp = employee.copy()
else:
    base_emp = snapshot[["employee_id"]].drop_duplicates() if "employee_id" in snapshot.columns else pd.DataFrame(columns=["employee_id"])

# attempt to compute latest salary/title/department if raw tables exist
latest_salary = latest_per_employee(salary, "from_date") if not salary.empty else pd.DataFrame()
if "amount" in latest_salary.columns:
    latest_salary = latest_salary[["employee_id","amount"]].rename(columns={"amount":"latest_salary"})
else:
    latest_salary = pd.DataFrame(columns=["employee_id","latest_salary"])

latest_title = latest_per_employee(title, "from_date")[["employee_id","title"]] if not title.empty and "title" in title.columns else pd.DataFrame(columns=["employee_id","title"])
latest_dept = pd.DataFrame()
if not dept_emp.empty and "dept_id" in dept_emp.columns and not department.empty and "dept_id" in department.columns:
    merged = dept_emp.merge(department, on="dept_id", how="left")
    latest_dept = latest_per_employee(merged, "to_date" if "to_date" in merged.columns else "from_date")[["employee_id","dept_name"]]
elif "dept_name" in snapshot.columns:
    latest_dept = snapshot[["employee_id","dept_name"]].drop_duplicates()

combined = base_emp.merge(latest_dept, on="employee_id", how="left") \
                   .merge(latest_title, on="employee_id", how="left") \
                   .merge(latest_salary, on="employee_id", how="left")

# fallback: if combined empty, use snapshot
if combined.empty:
    combined = snapshot.copy()

# ---------------- Overview page ----------------
def overview_page():
    st.markdown("<h1 style='text-align:center;'>HR Analytics Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p class='muted' style='text-align:center;'>Overview & Description</p>", unsafe_allow_html=True)
    st.markdown("---")

    # KPIs
    total_employees = len(combined) if "employee_id" in combined.columns else 0
    avg_salary = combined["latest_salary"].dropna().mean() if "latest_salary" in combined.columns else np.nan
    avg_age = combined["age"].dropna().mean() if "age" in combined.columns else np.nan
    with st.columns(3)[0]:
        pass
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Employees", f"{int(total_employees):,}")
    c2.metric("Avg Latest Salary", f"{avg_salary:,.0f}" if not np.isnan(avg_salary) else "N/A")
    c3.metric("Avg Age", f"{avg_age:.1f}" if not np.isnan(avg_age) else "N/A")

    # Overview charts (6)
    pal = PALETTES["overview"]

    # 1 Headcount timeline (if hire_date exists)
    if "hire_date" in employee.columns:
        emp = employee.copy()
        emp["hire_date"] = to_dt(emp["hire_date"])
        emp["hire_year"] = emp["hire_date"].dt.year
        hires = emp["hire_year"].value_counts().sort_index().reset_index()
        hires.columns = ["Year", "Hires"]
        if not hires.empty:
            fig = px.bar(hires, x="Year", y="Hires", title="Hires per Year", color="Hires", color_continuous_scale=pal["seq"])
            style_layout(fig)
            render_card("Hires per Year", fig, description="New hires by year", insights=["Shows hiring phases"], recs=["Plan recruitment ahead of peaks"])

    # 2 Current headcount by department
    if "dept_name" in combined.columns:
        dept_count = combined["dept_name"].value_counts().reset_index()
        dept_count.columns = ["Department", "Headcount"]
        if not dept_count.empty:
            fig = px.bar(dept_count, x="Department", y="Headcount", color="Headcount", color_continuous_scale=pal["seq"])
            style_layout(fig)
            render_card("Headcount by Department", fig, description="Current headcount per department", insights=["Capacity hotspots"], recs=["Align hiring with workload"])

    # 3 Gender mix (if exists)
    gcol = next((c for c in ["gender","sex","Gender","Sex"] if c in combined.columns), None)
    if gcol:
        counts = combined[gcol].value_counts(dropna=False).reset_index()
        counts.columns = ["Gender", "Count"]
        fig = px.pie(counts, names="Gender", values="Count", title="Gender Mix")
        style_layout(fig)
        render_card("Gender Mix", fig, description="Overall gender composition", insights=["Track D&I"], recs=["Diversify sourcing"])

    # 4 Salary distribution (latest)
    if "latest_salary" in combined.columns:
        s = combined["latest_salary"].dropna()
        if not s.empty:
            fig = px.histogram(s, x=s, nbins=40, title="Latest Salary Distribution")
            style_layout(fig)
            render_card("Salary Distribution", fig, description="Distribution of latest salaries", insights=["Skew/outliers"], recs=["Review banding"])

    # 5 Age distribution
    if "age" in combined.columns:
        a = combined["age"].dropna().astype(int).value_counts().sort_index().reset_index()
        a.columns = ["Age","Count"]
        if not a.empty:
            fig = px.bar(a, x="Age", y="Count", title="Age Distribution")
            style_layout(fig)
            render_card("Age Distribution", fig, description="Distribution by age", insights=["Dominant cohorts"], recs=["Customize L&D"])

    # 6 Tenure distribution
    if "company_tenure" in combined.columns:
        t = combined["company_tenure"].dropna()
        if not t.empty:
            fig = px.histogram(t, x=t, nbins=40, title="Company Tenure Distribution (yrs)")
            style_layout(fig)
            render_card("Tenure Distribution", fig, description="Employee tenure distribution", insights=["Early churn or long-tenured core"], recs=["Strengthen onboarding"])

# ---------------- Demographics page (6 charts) ----------------
def demographics_page():
    st.header("Demographics (6 charts)")
    pal = PALETTES["demographics"]

    # 1 Gender distribution
    gcol = next((c for c in ["gender","sex","Gender","Sex"] if c in combined.columns), None)
    if gcol:
        counts = combined[gcol].value_counts(dropna=False).reset_index()
        counts.columns = ["Gender","Count"]
        fig = px.pie(counts, names="Gender", values="Count", title="Gender Distribution")
        style_layout(fig)
        render_card("Gender Distribution", fig, description="Share by gender", insights=["Balance"], recs=["Diversity sourcing"])

    # 2 Age groups
    if "age" in combined.columns:
        df = combined.dropna(subset=["age"]).copy()
        if not df.empty:
            df["age_group"] = pd.cut(df["age"], bins=[15,25,35,45,55,65,75], labels=["16-24","25-34","35-44","45-54","55-64","65+"], right=False)
            ag = df["age_group"].value_counts().sort_index().reset_index()
            ag.columns = ["Age Group","Count"]
            fig = px.bar(ag, x="Age Group", y="Count", title="Age Group Distribution", color="Count", color_continuous_scale=pal["seq"])
            style_layout(fig)
            render_card("Age Group Distribution", fig, description="Counts per age bucket", insights=["Hiring focus"], recs=["Plan benefits by cohort"])

    # 3 Headcount by department
    if "dept_name" in combined.columns:
        d = combined["dept_name"].value_counts().reset_index()
        d.columns = ["Department","Headcount"]
        fig = px.bar(d, x="Department", y="Headcount", title="Headcount by Department", color="Headcount", color_continuous_scale=pal["seq"])
        style_layout(fig)
        render_card("Headcount by Department", fig, description="Where people are located", insights=["Over/understaffed areas"], recs=["Redistribute hires"])

    # 4 Titles top (top 15)
    if "title" in combined.columns:
        t = combined["title"].fillna("Unknown").value_counts().head(15).reset_index()
        t.columns = ["Title","Count"]
        fig = px.bar(t, x="Title", y="Count", title="Top Job Titles (Top 15)", color="Count", color_continuous_scale=pal["seq"])
        fig.update_xaxes(tickangle=45)
        style_layout(fig)
        render_card("Top Job Titles", fig, description="Most common roles", insights=["Key roles"], recs=["Cross-training critical roles"])

    # 5 Location (if exists)
    loc_col = next((c for c in ["location","office","office_location"] if c in combined.columns), None)
    if loc_col:
        l = combined[loc_col].value_counts().reset_index()
        l.columns = ["Location","Count"]
        fig = px.bar(l, x="Location", y="Count", title="Employees by Location", color="Count", color_continuous_scale=pal["seq"])
        style_layout(fig)
        render_card("Employees by Location", fig, description="Geographic spread", insights=["Concentration"], recs=["Local hiring strategy"])

    # 6 Employment type (if exists)
    emp_type_col = next((c for c in ["employment_type","emp_type","contract_type"] if c in combined.columns), None)
    if emp_type_col:
        e = combined[emp_type_col].value_counts().reset_index()
        e.columns = ["Type","Count"]
        fig = px.pie(e, names="Type", values="Count", title="Employment Type")
        style_layout(fig)
        render_card("Employment Type", fig, description="Full-time/part-time/contract split", insights=["Contract dependence"], recs=["Stabilize core roles"])

# ---------------- Salaries page (6 charts) ----------------
def salaries_page():
    st.header("Salaries & Compensation (6 charts)")
    pal = PALETTES["salaries"]

    # compute latest salary if available in salary table or snapshot
    latest_sal = latest_per_employee(salary, "from_date") if not salary.empty else pd.DataFrame()
    if "amount" in latest_sal.columns:
        latest_sal = latest_sal[["employee_id","amount"]].rename(columns={"amount":"latest_salary"})
    elif "latest_salary" in combined.columns:
        latest_sal = combined[["employee_id","latest_salary"]].dropna()

    # 1 Average salary over years (if salary.from_date)
    if "from_date" in salary.columns and "amount" in salary.columns and not salary.empty:
        s = salary.copy()
        s["from_date"] = to_dt(s["from_date"])
        s["year"] = s["from_date"].dt.year
        avg = s.groupby("year")["amount"].mean().reset_index()
        fig = px.line(avg, x="year", y="amount", markers=True, title="Average Salary Over Time")
        style_layout(fig)
        render_card("Avg Salary Over Time", fig, description="Mean salary per year", insights=["Trend"], recs=["Benchmark against market"])

    # 2 Salary distribution histogram (latest)
    if not latest_sal.empty:
        fig = px.histogram(latest_sal, x=latest_sal.columns[1], nbins=40, title="Latest Salary Distribution")
        style_layout(fig)
        render_card("Latest Salary Distribution", fig, description="Histogram of latest salaries", insights=["Outliers"], recs=["Review exceptions"])

    # 3 Avg salary by department
    if "dept_name" in combined.columns and not latest_sal.empty:
        merged = combined.merge(latest_sal, on="employee_id", how="left").dropna(subset=["dept_name", latest_sal.columns[1]])
        if not merged.empty:
            by_dept = merged.groupby("dept_name")[latest_sal.columns[1]].mean().reset_index().sort_values(by=latest_sal.columns[1], ascending=False)
            fig = px.bar(by_dept, x="dept_name", y=latest_sal.columns[1], title="Average Salary by Department", color=latest_sal.columns[1], color_continuous_scale=pal["seq"])
            fig.update_xaxes(tickangle=45)
            style_layout(fig)
            render_card("Avg Salary by Department", fig, description="Mean pay per department", insights=["High-paying units"], recs=["Benchmark critical roles"])

    # 4 Salary spread by department (strip)
    if "dept_name" in combined.columns and not latest_sal.empty:
        merged = combined.merge(latest_sal, on="employee_id", how="left").dropna(subset=["dept_name", latest_sal.columns[1]])
        fig = px.strip(merged, x="dept_name", y=latest_sal.columns[1], title="Salary Spread by Department", color="dept_name")
        fig.update_xaxes(tickangle=45)
        style_layout(fig)
        render_card("Salary Spread by Department", fig, description="Point distribution of salaries", insights=["Band overlap"], recs=["Standardize ranges"])

    # 5 Gender pay gap (if gender + salary exist)
    gcol = next((c for c in ["gender","sex","Gender","Sex"] if c in combined.columns), None)
    if gcol and not latest_sal.empty:
        m = combined.merge(latest_sal, on="employee_id", how="left").dropna(subset=[gcol, latest_sal.columns[1]])
        if not m.empty:
            gap = m.groupby(gcol)[latest_sal.columns[1]].mean().reset_index()
            fig = px.bar(gap, x=gcol, y=latest_sal.columns[1], title="Avg Salary by Gender", color=latest_sal.columns[1], color_continuous_scale=pal["seq"])
            style_layout(fig)
            render_card("Avg Salary by Gender", fig, description="Mean pay per gender", insights=["Potential gaps"], recs=["Run pay equity analysis"])

    # 6 Top salary growth % (employee level)
    if not salary.empty and "employee_id" in salary.columns and "amount" in salary.columns:
        g = salary.groupby("employee_id")["amount"].agg(["min","max"]).reset_index()
        g = g[g["min"]>0]
        if not g.empty:
            g["growth_pct"] = ((g["max"] - g["min"]) / g["min"]) * 100
            topg = g.sort_values("growth_pct", ascending=False).head(10)
            fig = px.bar(topg, x="employee_id", y="growth_pct", title="Top 10 Salary Growth %", color="growth_pct", color_continuous_scale=pal["seq"])
            style_layout(fig)
            render_card("Top Salary Growth %", fig, description="Largest % increases", insights=["Fast-tracked"], recs=["Audit fairness"])

# ---------------- Turnover & Tenure page (6 charts) ----------------
def turnover_page():
    st.header("Turnover & Tenure (6 charts)")
    pal = PALETTES["turnover"]

    # 1 Terminations per year
    if "termination_date" in employee.columns:
        emp = employee.copy()
        emp["termination_date"] = to_dt(emp["termination_date"])
        emp["term_year"] = emp["termination_date"].dt.year
        terms = emp["term_year"].dropna().value_counts().sort_index().reset_index()
        terms.columns = ["Year","Terminations"]
        if not terms.empty:
            fig = px.bar(terms, x="Year", y="Terminations", title="Terminations per Year", color="Terminations", color_continuous_scale=pal["seq"])
            style_layout(fig)
            render_card("Terminations per Year", fig, description="Annual exits", insights=["Spikes"], recs=["Investigate spikes"])

    # 2 New hires per year (hire_date)
    if "hire_date" in employee.columns:
        emp = employee.copy()
        emp["hire_date"] = to_dt(emp["hire_date"])
        emp["hire_year"] = emp["hire_date"].dt.year
        hires = emp["hire_year"].dropna().value_counts().sort_index().reset_index()
        hires.columns = ["Year","Hires"]
        if not hires.empty:
            fig = px.bar(hires, x="Year", y="Hires", title="New Hires per Year", color="Hires", color_continuous_scale=pal["seq"])
            style_layout(fig)
            render_card("New Hires per Year", fig, description="Annual hires", insights=["Hiring cycles"], recs=["Plan capacity"])

    # 3 Tenure distribution
    if "company_tenure" in combined.columns:
        t = combined["company_tenure"].dropna()
        if not t.empty:
            fig = px.histogram(t, x=t, nbins=40, title="Company Tenure Distribution (yrs)")
            style_layout(fig)
            render_card("Tenure Distribution", fig, description="Years at company", insights=["Early churn vs core"], recs=["Target onboarding"])

    # 4 Attrition rate by department (approx)
    if "dept_name" in combined.columns and "termination_date" in employee.columns:
        active = combined[["employee_id","dept_name"]]
        terms = employee.rename(columns={"id":"employee_id"})[["employee_id","termination_date"]] if "id" in employee.columns else employee[["employee_id","termination_date"]] if "employee_id" in employee.columns else pd.DataFrame()
        if not terms.empty:
            mm = active.merge(terms, on="employee_id", how="left")
            mm["left"] = mm["termination_date"].notna().astype(int)
            rate = mm.groupby("dept_name")["left"].mean().reset_index().rename(columns={"left":"attrition_rate"})
            if not rate.empty:
                fig = px.bar(rate, x="dept_name", y="attrition_rate", title="Attrition Rate by Dept", color="attrition_rate", color_continuous_scale=pal["seq"])
                fig.update_xaxes(tickangle=45)
                style_layout(fig)
                render_card("Attrition Rate by Dept", fig, description="Share who left", insights=["At-risk teams"], recs=["Stay interviews"])

    # 5 Early attrition (<=1 year) if hire & termination exist
    if "hire_date" in employee.columns and "termination_date" in employee.columns:
        ee = employee.copy()
        ee["hire_date"] = to_dt(ee["hire_date"])
        ee["termination_date"] = to_dt(ee["termination_date"])
        ee["tenure_years"] = (ee["termination_date"] - ee["hire_date"]).dt.days / 365.25
        early = ee[ee["tenure_years"].notna() & (ee["tenure_years"] <= 1)]
        counts = early.shape[0]
        fig = None
        # simple pie of early vs others if we have counts
        total_terms = ee[ee["termination_date"].notna()].shape[0]
        if total_terms > 0:
            dfp = pd.DataFrame({
                "Status":["<=1 year",">1 year"],
                "Count":[counts, total_terms - counts]
            })
            fig = px.pie(dfp, names="Status", values="Count", title="Early Attrition (<=1yr)")
            style_layout(fig)
            render_card("Early Attrition (<=1yr)", fig, description="Share leaving early", insights=["Onboarding issues"], recs=["Improve 30/60/90 onboarding"])

    # 6 Department moves per employee (proxy for transfers)
    if not dept_emp.empty and "employee_id" in dept_emp.columns:
        moves = dept_emp.groupby("employee_id").size().reset_index(name="moves")
        mv = moves["moves"].value_counts().reset_index()
        mv.columns = ["Moves","Employees"]
        fig = px.bar(mv, x="Moves", y="Employees", title="Dept Moves per Employee", color="Employees", color_continuous_scale=pal["seq"])
        style_layout(fig)
        render_card("Dept Moves per Employee", fig, description="Internal mobility proxy", insights=["Mobility health"], recs=["Promote internal roles"])

# ---------------- Promotions & Performance page (6 charts) ----------------
def promotions_page():
    st.header("Promotions & Performance (6 charts)")
    pal = PALETTES["promotions"]

    # promotions derived from title changes
    promos_df = pd.DataFrame()
    if not title.empty and {"employee_id","title","from_date"}.issubset(title.columns):
        tdf = title.copy()
        tdf["from_date"] = to_dt(tdf["from_date"])
        tdf = tdf.sort_values(["employee_id","from_date"])
        tdf["prev_title"] = tdf.groupby("employee_id")["title"].shift()
        tdf["changed"] = (tdf["title"] != tdf["prev_title"]).astype(int)
        promos_df = tdf

    # 1 Promotions per year
    if not promos_df.empty:
        per_year = promos_df[promos_df["changed"]==1].groupby(promos_df["from_date"].dt.year).size().reset_index(name="Promotions")
        per_year.columns = ["Year","Promotions"]
        fig = px.bar(per_year, x="Year", y="Promotions", title="Promotions per Year", color="Promotions", color_continuous_scale=pal["seq"])
        style_layout(fig)
        render_card("Promotions per Year", fig, description="Count of title changes", insights=["Promotion waves"], recs=["Calibrate promotion cycles"])

    # 2 Time to first promotion (if hire_date exists)
    if not promos_df.empty and "hire_date" in employee.columns:
        first = promos_df[promos_df["changed"]==1].groupby("employee_id")["from_date"].min().reset_index().rename(columns={"from_date":"first_promo_date"})
        if "employee_id" in employee.columns:
            emp_join = employee[["employee_id","hire_date"]].copy()
        else:
            emp_join = employee.rename(columns={"id":"employee_id"})[["employee_id","hire_date"]].copy() if "id" in employee.columns else pd.DataFrame()
        if not emp_join.empty and not first.empty:
            dfp = emp_join.merge(first, on="employee_id", how="inner")
            dfp["hire_date"] = to_dt(dfp["hire_date"])
            dfp["time_to_first_promo_years"] = (to_dt(dfp["first_promo_date"]) - dfp["hire_date"]).dt.days/365.25
            dfp = dfp.dropna(subset=["time_to_first_promo_years"])
            if not dfp.empty:
                fig = px.histogram(dfp, x="time_to_first_promo_years", nbins=30, title="Time to First Promotion (yrs)")
                style_layout(fig)
                render_card("Time to First Promotion", fig, description="Distribution of time until first promotion", insights=["Long waits reduce retention"], recs=["Publish promotion SLAs"])

    # 3 Employees with multiple promotions (top 20)
    if not promos_df.empty:
        cnt = promos_df.groupby("employee_id")["changed"].sum().reset_index().rename(columns={"changed":"promotion_count"})
        if not cnt.empty:
            top = cnt.sort_values("promotion_count", ascending=False).head(20)
            fig = px.bar(top, x="employee_id", y="promotion_count", title="Employees with Multiple Promotions (Top 20)", color="promotion_count", color_continuous_scale=pal["seq"])
            style_layout(fig)
            render_card("Multiple Promotions", fig, description="High trajectory employees", insights=["Potential leaders"], recs=["Design leadership programs"])

    # 4 Promotions by department
    if not promos_df.empty and "dept_name" in combined.columns:
        pm = promos_df[promos_df["changed"]==1][["employee_id"]].drop_duplicates()
        pm = pm.merge(combined[["employee_id","dept_name"]], on="employee_id", how="left")
        byd = pm.groupby("dept_name").size().reset_index(name="promotions")
        if not byd.empty:
            fig = px.bar(byd, x="dept_name", y="promotions", title="Promotions by Department", color="promotions", color_continuous_scale=pal["seq"])
            fig.update_xaxes(tickangle=45)
            style_layout(fig)
            render_card("Promotions by Department", fig, description="Where promotions happen", insights=["Career-rich units"], recs=["Spread mobility to flat units"])

    # 5 Performance ratings distribution (if exists)
    perf_col = next((c for c in ["performance_rating","perf_rating","rating"] if c in combined.columns), None)
    if perf_col:
        p = combined[perf_col].value_counts().reset_index()
        p.columns = [perf_col, "Count"]
        fig = px.bar(p, x=perf_col, y="Count", title="Performance Rating Distribution", color="Count", color_continuous_scale=pal["seq"])
        style_layout(fig)
        render_card("Performance Ratings", fig, description="Distribution of performance ratings", insights=["Calibration needs"], recs=["Calibrate rating scales"])

    # 6 Title steps per employee (career path length)
    if not title.empty and "employee_id" in title.columns:
        steps = title.groupby("employee_id").size().reset_index(name="steps")
        fig = px.histogram(steps, x="steps", nbins=20, title="Title Steps per Employee (Career Path Length)")
        style_layout(fig)
        render_card("Career Path Length", fig, description="Number of title records per employee", insights=["Flat vs dynamic paths"], recs=["Offer lateral moves"])

# ---------------- Router ----------------
if page == "Overview":
    overview_page()
elif page == "Demographics":
    demographics_page()
elif page == "Salaries":
    salaries_page()
elif page == "Turnover & Tenure":
    turnover_page()
elif page == "Promotions & Performance":
    promotions_page()
else:
    overview_page()

st.markdown("<div class='muted'>All charts are guarded: if required columns are missing in your CSVs the chart will be skipped (no crash).</div>", unsafe_allow_html=True)
