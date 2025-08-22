# hr_analytics_app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# =========================== PAGE CONFIG ===========================
st.set_page_config(page_title="HR Analytics Dashboard", layout="wide")

# Clear deprecated query params safely (Streamlit >= 1.32)
if hasattr(st, "query_params"):
    try:
        st.query_params.clear()
    except Exception:
        pass

# =========================== THEME SWITCH ==========================
with st.sidebar:
    st.markdown("## Settings")
    dark_mode = st.toggle("Dark Mode", value=True, help="Toggle between Dark and Light themes")
    st.caption("Use the chart modebar to download PNGs.")

UI = {
    "text": "#e5e7eb" if dark_mode else "#0f172a",
    "bg": "#0b1021" if dark_mode else "#ffffff",
    "panel": "#111827" if dark_mode else "#f8fafc",
}
PLOTLY_TEMPLATE = "plotly_dark" if dark_mode else "plotly_white"

PALETTES = {
    "demographics": {
        "seq": px.colors.sequential.Blues,
        "primary": "#2563eb",
        "accent": "#06b6d4",
    },
    "salaries": {
        "seq": px.colors.sequential.Greens,
        "primary": "#16a34a",
        "accent": "#84cc16",
    },
    "promotions": {
        "seq": px.colors.sequential.Purples,
        "primary": "#7c3aed",
        "accent": "#ec4899",
    },
    "retention": {
        "seq": px.colors.sequential.OrRd,
        "primary": "#f97316",
        "accent": "#ef4444",
    },
    "overview": {
        "seq": px.colors.sequential.Viridis,
        "primary": "#6366f1",
        "accent": "#14b8a6",
    }
}

st.markdown(f"""
<style>
  .stApp {{ background:{UI['bg']}; color:{UI['text']}; }}
  .block-container {{ padding-top: 0.8rem; }}
  h1,h2,h3,h4,h5,h6 {{ color: {("#cbd5e1" if dark_mode else "#0f172a")} !important; }}
  .card {{
    background:{UI['panel']};
    border-radius:16px; padding:1rem; margin-bottom:1rem; border:1px solid rgba(148,163,184,.15);
  }}
  .desc {{ opacity:.95; }}
  .muted {{ opacity:.75; }}
  .nav-btn > button {{
    width: 100%;
    border-radius: 10px !important;
    font-weight: 600 !important;
  }}
</style>
""", unsafe_allow_html=True)

# =============================== HELPERS ===============================
def to_dt(s):
    return pd.to_datetime(s, errors="coerce")

def style_fig(fig, section: str, height: int | None = None, title: str | None = None):
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=UI["text"], size=14),
        title=dict(text=title, x=0.02, xanchor="left") if title else None
    )
    if height:
        fig.update_layout(height=height)
    return fig

def safe_has(df: pd.DataFrame, cols) -> bool:
    return set(cols).issubset(df.columns)

@st.cache_data
def latest_per_group(df, by, sort_col):
    d = df.copy()
    if sort_col not in d.columns:
        d[sort_col] = pd.Timestamp("1970-01-01")
    return d.sort_values([by, sort_col]).groupby(by, as_index=False).tail(1)

def render_card(section: str, title: str, fig=None, table: pd.DataFrame | None=None,
                description: str = "", insights: list[str] | None=None, recs: list[str] | None=None):
    st.markdown(f"<div class='card'><h3>{title}</h3>", unsafe_allow_html=True)
    if fig is not None:
        st.plotly_chart(style_fig(fig, section), use_container_width=True)
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

# =============================== DATA ================================
@st.cache_data
def load_data():
    # Required CSV files in the same folder
    salary = pd.read_csv("salary.csv")
    employee = pd.read_csv("employee.csv")
    current = pd.read_csv("current_employee_snapshot.csv")
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

    # Build base employee snapshot with safe columns
    emp = employee.rename(columns={"id":"employee_id"}).copy()
    if "employee_id" not in emp.columns:
        # Create one if missing (prevents crashes but charts will be limited)
        emp["employee_id"] = np.arange(1, len(emp) + 1)

    # Age
    if "birth_date" in emp.columns:
        emp["age"] = datetime.now().year - emp["birth_date"].dt.year
    else:
        emp["age"] = np.nan

    # Tenure
    if "hire_date" in emp.columns:
        emp["company_tenure"] = (pd.Timestamp.today() - emp["hire_date"]).dt.days/365.25
    else:
        emp["company_tenure"] = np.nan

    # Latest department
    if safe_has(dept_emp, ["employee_id", "dept_id"]) and safe_has(department, ["dept_id", "dept_name"]):
        d = dept_emp.merge(department, on="dept_id", how="left")
        dept_latest = latest_per_group(d, "employee_id", "to_date" if "to_date" in d.columns else "from_date")[["employee_id", "dept_id", "dept_name"]]
    else:
        # Fallback to current snapshot columns if present
        cols = [c for c in ["employee_id", "dept_name"] if c in current.columns]
        dept_latest = current[cols].drop_duplicates() if cols else pd.DataFrame(columns=["employee_id","dept_name"])

    # Latest title
    if safe_has(title, ["employee_id", "title"]):
        title_latest = latest_per_group(title, "employee_id", "to_date" if "to_date" in title.columns else "from_date")[["employee_id","title"]]
    else:
        cols = [c for c in ["employee_id","title"] if c in current.columns]
        title_latest = current[cols].drop_duplicates() if cols else pd.DataFrame(columns=["employee_id","title"])

    # Latest salary
    if safe_has(salary, ["employee_id","amount"]):
        sal_latest = latest_per_group(salary, "employee_id", "from_date" if "from_date" in salary.columns else "amount")[["employee_id","amount"]]
        sal_latest = sal_latest.rename(columns={"amount":"latest_salary"})
    else:
        sal_latest = pd.DataFrame(columns=["employee_id","latest_salary"])

    # Combine into snapshot
    snapshot = emp.merge(dept_latest, on="employee_id", how="left") \
                  .merge(title_latest, on="employee_id", how="left") \
                  .merge(sal_latest, on="employee_id", how="left")

    # Add any extra columns from current snapshot if available
    extra_cols = [c for c in current.columns if c not in snapshot.columns and c != "employee_id"]
    if extra_cols:
        snapshot = snapshot.merge(current[["employee_id"] + extra_cols], on="employee_id", how="left")

    # Guarantee presence of frequently used columns
    for c in ["dept_name", "title", "company_tenure", "age", "latest_salary"]:
        if c not in snapshot.columns:
            snapshot[c] = np.nan

    return salary, employee, snapshot, dept_emp, department, dept_mgr, title

salary, employee, snapshot, dept_emp, department, dept_mgr, title = load_data()

# =============================== NAVIGATION ===============================
PAGES = ["Overview", "Demographics", "Salaries", "Promotions", "Retention"]
if "page" not in st.session_state:
    st.session_state.page = "Overview"

col_nav = st.columns(5)
for i, p in enumerate(PAGES):
    with col_nav[i]:
        if st.button(p, key=f"nav_{p}", use_container_width=True, type="primary" if st.session_state.page==p else "secondary"):
            st.session_state.page = p

st.markdown("---")

# =============================== OVERVIEW PAGE ===============================
def render_overview():
    st.markdown("<h1 style='text-align:center;'>HR Analytics Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p class='muted' style='text-align:center;'>A multi-section dashboard with 30 interactive Plotly charts and a unified theme switch.</p>", unsafe_allow_html=True)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### What this app does")
    st.markdown("""
- Loads HR core datasets (employees, salaries, titles, departments, current snapshot).
- Builds a robust snapshot of current state (latest title, department, salary), plus age and tenure.
- Presents **30 charts** across 4 analytical sections:
  1) **Demographics (8 charts)** — age, gender mix (if exists), headcount distribution.
  2) **Salaries & Compensation (8 charts)** — pay levels, growth, spreads, percentiles.
  3) **Promotions & Career Growth (7 charts)** — promotion cadence, time-to-first-promo, heatmaps.
  4) **Retention & Turnover (7 charts)** — tenure, attrition, transfers.
- Provides descriptions, insights, and actionable recommendations under each chart.
- Dark/Light theme switch and section-specific color palettes.
""")
    st.markdown("### Files expected")
    st.code("salary.csv, employee.csv, current_employee_snapshot.csv, department.csv, department_employee.csv, department_manager.csv, title.csv", language="text")
    st.markdown("### Notes")
    st.markdown("""
- The app is **defensive**: charts render only when required columns exist.
- No deprecated or experimental reruns; no OLS trendline dependency.
- If your schema differs, update the guards or column names accordingly.
""")
    st.markdown("</div>", unsafe_allow_html=True)

    # Quick KPIs (if data available)
    with st.container():
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Employees (snapshot rows)", value=f"{len(snapshot):,}")
        with c2:
            hc = snapshot['dept_name'].nunique() if 'dept_name' in snapshot.columns else 0
            st.metric("Departments", value=f"{hc:,}")
        with c3:
            avg_sal = snapshot['latest_salary'].dropna().mean() if 'latest_salary' in snapshot.columns else np.nan
            st.metric("Avg Latest Salary", value=f"{avg_sal:,.0f}" if pd.notna(avg_sal) else "N/A")
        with c4:
            avg_age = snapshot['age'].dropna().mean() if 'age' in snapshot.columns else np.nan
            st.metric("Avg Age", value=f"{avg_age:,.1f}" if pd.notna(avg_age) else "N/A")

# =============================== DEMOGRAPHICS (8) ===============================
def render_demographics():
    pal = PALETTES["demographics"]

    # 1) Age distribution
    if 'age' in snapshot.columns:
        age_counts = snapshot['age'].dropna().astype(int).value_counts().sort_index().reset_index()
        age_counts.columns = ['Age','Count']
        fig = px.bar(age_counts, x='Age', y='Count', color='Count', color_continuous_scale=pal['seq'])
        render_card("demographics", "Age Distribution", fig,
                    description="Distribution of current employees by age (years).",
                    insights=["Identify dominant age bands and gaps."],
                    recs=["Tailor benefits and learning paths to dominant age groups."])

    # 2) Age group composition by department
    if safe_has(snapshot, ['age','dept_name']):
        df = snapshot.copy()
        df['age_group'] = pd.cut(df['age'], bins=[10,20,30,40,50,60,70], labels=['10s','20s','30s','40s','50s','60s'], right=False)
        grp = df.pivot_table(index='dept_name', columns='age_group', values='employee_id', aggfunc='count', fill_value=0).reset_index()
        fig = px.bar(grp, x='dept_name', y=grp.columns[1:], barmode='stack', color_discrete_sequence=pal['seq'])
        fig.update_xaxes(tickangle=45)
        render_card("demographics", "Age Group Composition by Department", fig,
                    description="Stacked headcount by age group for each department.",
                    insights=["Departments with skewed age structure become visible."],
                    recs=["Balance hiring to reduce succession risk."])

    # 3) Headcount by department
    if 'dept_name' in snapshot.columns:
        dept_dist = snapshot['dept_name'].dropna().value_counts().reset_index()
        dept_dist.columns = ['Department','Headcount']
        fig = px.bar(dept_dist, x='Department', y='Headcount', color='Headcount', color_continuous_scale=pal['seq'])
        render_card("demographics", "Headcount by Department", fig,
                    description="Current headcount by department.",
                    insights=["Capacity hotspots and understaffed units."],
                    recs=["Align hiring plans with workload."])

    # 4) Headcount by title (Top 20)
    if 'title' in snapshot.columns:
        title_counts = snapshot['title'].fillna('Unknown').value_counts().head(20).reset_index()
        title_counts.columns = ['Title','Headcount']
        fig = px.bar(title_counts, x='Title', y='Headcount', color='Headcount', color_continuous_scale=pal['seq'])
        fig.update_xaxes(tickangle=45)
        render_card("demographics", "Headcount by Job Title (Top 20)", fig,
                    description="Most common roles across the organization.",
                    insights=["Dominant roles and potential single-point dependencies."],
                    recs=["Cross-train and plan backups for critical roles."])

    # 5) Age by department (box)
    if safe_has(snapshot, ['age','dept_name']):
        fig = px.box(snapshot.dropna(subset=['age','dept_name']), x='dept_name', y='age', color='dept_name')
        fig.update_xaxes(tickangle=45, title="")
        render_card("demographics", "Age Distribution by Department (Box)", fig,
                    description="Spread and median age by department.",
                    insights=["Outlier-heavy teams may need tailored wellbeing programs."],
                    recs=["Review workload design in teams with very wide age spread."])

    # 6) Gender mix overall
    gcol = next((c for c in ["gender","sex","Gender","Sex"] if c in snapshot.columns), None)
    if gcol:
        counts = snapshot[gcol].value_counts(dropna=False).reset_index()
        counts.columns = ['Gender','Count']
        fig = px.pie(counts, names='Gender', values='Count', color='Gender')
        render_card("demographics", "Gender Mix (Overall)", fig,
                    description="Gender composition across the company.",
                    insights=["Detect imbalance and track diversity goals."],
                    recs=["Widen sourcing channels and ensure unbiased screening."])

    # 7) Gender ratio by department
    if gcol and 'dept_name' in snapshot.columns:
        gdept = snapshot[[gcol,'dept_name']].dropna().value_counts().reset_index(name='Count')
        gdept.rename(columns={gcol:'Gender'}, inplace=True)
        fig = px.bar(gdept, x='dept_name', y='Count', color='Gender', barmode='stack')
        render_card("demographics", "Gender Ratio by Department", fig,
                    description="Gender distribution per department.",
                    insights=["Spot departments with skewed ratios."],
                    recs=["Set local targets and mentorship for underrepresented groups."])

    # 8) Age vs Tenure (heatmap)
    if safe_has(snapshot, ['age','company_tenure']):
        fig = px.density_heatmap(snapshot.dropna(subset=['age','company_tenure']),
                                 x='age', y='company_tenure', nbinsx=20, nbinsy=20,
                                 color_continuous_scale=pal['seq'])
        render_card("demographics", "Age vs Tenure (Heatmap)", fig,
                    description="Density of employees across age and company tenure.",
                    insights=["Clusters indicate career stage concentrations."],
                    recs=["Design stage-specific L&D and retention programs."])

# =============================== SALARIES (8) ===============================
def render_salaries():
    pal = PALETTES["salaries"]

    # 1) Average salary over time
    if safe_has(salary, ["employee_id","amount","from_date"]):
        df = salary.copy()
        df['from_date'] = to_dt(df['from_date'])
        df['year'] = df['from_date'].dt.year
        avg_salary_per_year = df.groupby('year')['amount'].mean().reset_index()
        fig = px.line(avg_salary_per_year, x='year', y='amount', markers=True)
        render_card("salaries", "Average Salary Over Time", fig,
                    description="Year-over-year average compensation.",
                    insights=["Identify acceleration or stagnation in pay growth."],
                    recs=["Budget merit increases aligned with market benchmarks."])

    # 2) Top 20 salaries (table)
    if safe_has(salary, ["employee_id","amount"]):
        top = salary.groupby('employee_id')['amount'].max().sort_values(ascending=False).head(20).reset_index()
        top.columns = ['Employee ID', 'Top Salary']
        render_card("salaries", "Top 20 Salaries (Table)", None, top,
                    description="Highest recorded salary per employee.",
                    insights=["Outliers and executive bands."],
                    recs=["Ensure pay governance and internal parity checks."])

    # 3) Salary histogram (latest)
    if safe_has(salary, ["employee_id","amount"]):
        latest_sal = latest_per_group(salary, 'employee_id', 'from_date')
        fig = px.histogram(latest_sal, x='amount', nbins=40, color_discrete_sequence=[pal['primary']])
        render_card("salaries", "Salary Distribution (Latest)", fig,
                    description="Histogram of latest salary amounts.",
                    insights=["Skewness indicates band compression or outliers."],
                    recs=["Review ranges; consider mid-point corrections."])

    # 4) Average salary by department
    if 'dept_name' in snapshot.columns and safe_has(salary, ["employee_id","amount"]):
        base = snapshot[['employee_id','dept_name']].dropna()
        merged = base.merge(salary[['employee_id','amount']], on='employee_id', how='left').dropna(subset=['amount'])
        dept_avg = merged.groupby('dept_name')['amount'].mean().reset_index().sort_values('amount', ascending=False)
        fig = px.bar(dept_avg, x='dept_name', y='amount', color='amount', color_continuous_scale=pal['seq'])
        fig.update_xaxes(tickangle=45)
        render_card("salaries", "Average Salary by Department", fig,
                    description="Mean compensation per department.",
                    insights=["High-paying functions vs support units."],
                    recs=["Benchmark against market; adjust for critical roles."])

    # 5) Tenure vs salary (latest) — no trendline dependency
    if 'company_tenure' in snapshot.columns and safe_has(salary, ["employee_id","amount"]):
        base = snapshot[['employee_id','company_tenure']]
        merged = base.merge(latest_per_group(salary, 'employee_id', 'from_date')[['employee_id','amount']],
                            on='employee_id', how='left')
        fig = px.scatter(merged, x='company_tenure', y='amount', trendline=None)
        render_card("salaries", "Tenure vs Salary (Latest)", fig,
                    description="Relationship between years in company and current pay.",
                    insights=["Weak correlation may signal pay policy issues."],
                    recs=["Define progression bands tied to tenure and performance."])

    # 6) Top 10 salary growth %
    if safe_has(salary, ["employee_id","amount"]):
        g = salary.groupby('employee_id')['amount'].agg(['min','max']).reset_index()
        g = g[g['min']>0]
        g['growth_%'] = ((g['max']-g['min'])/g['min'])*100
        topg = g.sort_values('growth_%', ascending=False).head(10)
        fig = px.bar(topg, x='employee_id', y='growth_%', color='growth_%', color_continuous_scale=pal['seq'])
        render_card("salaries", "Top 10 Salary Growth %", fig,
                    description="Largest percentage increase from first to latest salary.",
                    insights=["Fast-trackers or compression adjustments."],
                    recs=["Audit fairness; align with performance outcomes."])

    # 7) Salary spread by department (strip)
    if 'dept_name' in snapshot.columns and safe_has(salary, ["employee_id","amount"]):
        base = snapshot[['employee_id','dept_name']]
        merged = base.merge(latest_per_group(salary, 'employee_id', 'from_date')[['employee_id','amount']],
                            on='employee_id', how='left').dropna(subset=['dept_name','amount'])
        fig = px.strip(merged, x='dept_name', y='amount', color='dept_name')
        fig.update_xaxes(tickangle=45)
        render_card("salaries", "Salary Spread by Department", fig,
                    description="Point distribution of latest salaries per department.",
                    insights=["Identify outliers and band overlaps."],
                    recs=["Standardize ranges; review exception approvals."])

    # 8) Average salary by title (Top 30)
    if safe_has(salary, ["employee_id","amount"]) and 'title' in snapshot.columns:
        base = snapshot[['employee_id','title']].copy()
        base['title'] = base['title'].fillna('Unknown')
        merged = base.merge(latest_per_group(salary,'employee_id','from_date')[['employee_id','amount']],
                            on='employee_id', how='left').dropna(subset=['amount'])
        avg_t = merged.groupby('title')['amount'].mean().reset_index().sort_values('amount', ascending=False).head(30)
        fig = px.bar(avg_t, x='title', y='amount')
        fig.update_xaxes(tickangle=45, title="")
        render_card("salaries", "Average Salary by Job Title (Top 30)", fig,
                    description="Mean latest pay for the top 30 titles.",
                    insights=["Identify premium roles and pay gaps."],
                    recs=["Run pay equity analysis within similar bands."])

# =============================== PROMOTIONS (7) ===============================
def render_promotions():
    pal = PALETTES["promotions"]

    promos = None
    if safe_has(title, ["employee_id","title","from_date"]):
        tdf = title.copy()
        tdf['from_date'] = to_dt(tdf['from_date'])
        tdf = tdf.sort_values(['employee_id','from_date'])
        tdf['prev_title'] = tdf.groupby('employee_id')['title'].shift()
        tdf['changed'] = (tdf['title'] != tdf['prev_title']).astype(int)
        promos = tdf.groupby('employee_id')['changed'].sum().reset_index(name='promotion_count')
        tdf['year'] = tdf['from_date'].dt.year

        # 1) Promotions per year
        per_year = tdf[tdf['changed']==1].groupby('year').size().reset_index(name='Promotions')
        fig = px.bar(per_year, x='year', y='Promotions', color='Promotions', color_continuous_scale=pal['seq'])
        render_card("promotions", "Promotions per Year", fig,
                    description="Count of title changes by year.",
                    insights=["Waves of career moves; hiring vs promotion strategy."],
                    recs=["Stabilize cadence with clear career frameworks."])

        # 2) Time to first promotion
        if safe_has(employee, ['id','hire_date']):
            first_change = tdf[tdf['changed']==1].groupby('employee_id')['from_date'].min().reset_index().rename(columns={'from_date':'first_promo_date'})
            tmp = employee.rename(columns={'id':'employee_id'})[['employee_id','hire_date']].merge(first_change, on='employee_id', how='inner')
            tmp['time_to_first_promo_years'] = (to_dt(tmp['first_promo_date']) - to_dt(tmp['hire_date'])).dt.days/365.25
            fig = px.histogram(tmp, x='time_to_first_promo_years', nbins=30, color_discrete_sequence=[pal['primary']])
            render_card("promotions", "Time to First Promotion (Years)", fig,
                        description="Distribution of tenure before first promotion.",
                        insights=["Long lags may harm retention of top talent."],
                        recs=["Publish SLA for promotion timelines and criteria."])

        # 3) Promotions by department
        if 'dept_name' in snapshot.columns:
            pmap = promos.merge(snapshot[['employee_id','dept_name']], on='employee_id', how='left')
            by_dept = pmap.groupby('dept_name')['promotion_count'].sum().reset_index().sort_values('promotion_count', ascending=False)
            fig = px.bar(by_dept, x='dept_name', y='promotion_count', color='promotion_count', color_continuous_scale=pal['seq'])
            fig.update_xaxes(tickangle=45)
            render_card("promotions", "Promotions by Department (Total)", fig,
                        description="Total promotions mapped to employees' current departments.",
                        insights=["Career-progressive units vs flat structures."],
                        recs=["Create internal mobility lanes in flat units."])

        # 4) Multi-promotion employees (Top 20)
        top_multi = promos.sort_values('promotion_count', ascending=False).head(20)
        fig = px.bar(top_multi, x='employee_id', y='promotion_count', color='promotion_count', color_continuous_scale=pal['seq'])
        render_card("promotions", "Employees with Multiple Promotions (Top 20)", fig,
                    description="Employees who got the most title changes.",
                    insights=["High-trajectory talent clusters."],
                    recs=["Design leadership programs for high-potentials."])

        # 5) Promotions by gender
        gcol = next((c for c in ["gender","sex","Gender","Sex"] if c in snapshot.columns), None)
        if gcol:
            m = promos.merge(snapshot[['employee_id',gcol]], on='employee_id', how='left')
            by_g = m.groupby(gcol)['promotion_count'].sum().reset_index().rename(columns={gcol:'Gender'})
            fig = px.bar(by_g, x='Gender', y='promotion_count', color='promotion_count', color_continuous_scale=pal['seq'])
            render_card("promotions", "Promotions by Gender", fig,
                        description="Total promotions aggregated by gender.",
                        insights=["Detect bias or pipeline gaps."],
                        recs=["Run calibrated promotion panels; track ratios quarterly."])

        # 6) Career path length (title steps)
        path_len = title.groupby('employee_id').size().reset_index(name='title_steps')
        fig = px.histogram(path_len, x='title_steps', nbins=20, color_discrete_sequence=[pal['primary']])
        render_card("promotions", "Career Path Length (Title Steps)", fig,
                    description="How many title records per employee (proxy for moves).",
                    insights=["Flat paths vs dynamic careers."],
                    recs=["Offer lateral moves where vertical ladders are short."])

        # 7) Promotions heatmap (dept x year)
        if 'dept_name' in snapshot.columns:
            mm = tdf[tdf['changed']==1].merge(snapshot[['employee_id','dept_name']], on='employee_id', how='left')
            heat = mm.pivot_table(index='dept_name', columns='year', values='employee_id', aggfunc='count', fill_value=0)
            fig = px.imshow(heat, aspect='auto', color_continuous_scale=pal['seq'])
            render_card("promotions", "Promotions Heatmap (Dept × Year)", fig,
                        description="Where/when promotions cluster.",
                        insights=["Timing and departmental cadence of promotions."],
                        recs=["Smooth promotion cycles to reduce churn risk."])

# =============================== RETENTION (7) ===============================
def render_retention():
    pal = PALETTES["retention"]

    # 1) Tenure distribution
    if 'company_tenure' in snapshot.columns:
        fig = px.histogram(snapshot.dropna(subset=['company_tenure']), x='company_tenure', nbins=40, color_discrete_sequence=[pal['primary']])
        render_card("retention", "Tenure Distribution (Years)", fig,
                    description="Histogram of employee time in company.",
                    insights=["Heavy early churn or long-tenured core."],
                    recs=["Target onboarding/mentorship to reduce early exits."])

    # 2) Tenure by department (box)
    if safe_has(snapshot, ['dept_name','company_tenure']):
        fig = px.box(snapshot.dropna(subset=['dept_name','company_tenure']), x='dept_name', y='company_tenure', color='dept_name')
        fig.update_xaxes(tickangle=45, title="")
        render_card("retention", "Tenure by Department (Box)", fig,
                    description="Spread and median tenure by department.",
                    insights=["Units with systematic early churn."],
                    recs=["Audit managers' onboarding and workload allocation."])

    # 3) New hires per year
    if 'hire_date' in employee.columns:
        hires = employee.rename(columns={'id':'employee_id'}).copy()
        hires['year'] = to_dt(hires['hire_date']).dt.year
        by_year = hires['year'].value_counts().sort_index().reset_index()
        by_year.columns = ['Year','New Hires']
        fig = px.bar(by_year, x='Year', y='New Hires', color='New Hires', color_continuous_scale=pal['seq'])
        render_card("retention", "New Hires per Year", fig,
                    description="Annual intake volume.",
                    insights=["Scaling phases and hiring freezes."],
                    recs=["Capacity plan recruiting with business cycles."])

    # 4) Terminations per year
    if 'termination_date' in employee.columns:
        terms = employee.rename(columns={'id':'employee_id'}).copy()
        terms['year'] = to_dt(terms['termination_date']).dt.year
        terms = terms.dropna(subset=['year'])
        if not terms.empty:
            t_year = terms['year'].value_counts().sort_index().reset_index()
            t_year.columns = ['Year','Terminations']
            fig = px.bar(t_year, x='Year', y='Terminations', color='Terminations', color_continuous_scale=pal['seq'])
            render_card("retention", "Terminations per Year", fig,
                        description="Annual employee exits (if data available).",
                        insights=["Attrition spikes or stabilization."],
                        recs=["Root-cause analysis during spikes; manager coaching."])

    # 5) Attrition rate by department
    if 'dept_name' in snapshot.columns and 'termination_date' in employee.columns:
        active = snapshot[['employee_id','dept_name']]
        terms = employee.rename(columns={'id':'employee_id'})[['employee_id','termination_date']]
        mm = active.merge(terms, on='employee_id', how='left')
        mm['has_left'] = mm['termination_date'].notna().astype(int)
        rate = mm.groupby('dept_name')['has_left'].mean().reset_index().rename(columns={'has_left':'attrition_rate'})
        fig = px.bar(rate, x='dept_name', y='attrition_rate', color='attrition_rate', color_continuous_scale=pal['seq'])
        fig.update_xaxes(tickangle=45)
        render_card("retention", "Attrition Rate by Department", fig,
                    description="Share of employees with termination record per department.",
                    insights=["At-risk teams."],
                    recs=["Early-warning dashboards & stay interviews."])

    # 6) Tenure vs Salary (heatmap)
    if safe_has(salary, ["employee_id","amount"]) and 'company_tenure' in snapshot.columns:
        latest_sal = latest_per_group(salary, 'employee_id', 'from_date')
        mm = snapshot[['employee_id','company_tenure']].merge(latest_sal[['employee_id','amount']], on='employee_id', how='left').dropna()
        fig = px.density_heatmap(mm, x='company_tenure', y='amount', nbinsx=25, nbinsy=25, color_continuous_scale=pal['seq'])
        render_card("retention", "Tenure vs Salary (Heatmap)", fig,
                    description="Joint distribution of tenure and pay.",
                    insights=["Plateaus or rapid pay growth with tenure."],
                    recs=["Define step increases & promotions to reduce plateaus."])

    # 7) Department moves per employee
    if 'employee_id' in dept_emp.columns:
        counts = dept_emp.groupby('employee_id').size().reset_index(name='dept_moves')
        moves = counts['dept_moves'].value_counts().reset_index(); moves.columns = ['Moves','Employees']
        fig = px.bar(moves, x='Moves', y='Employees', color='Employees', color_continuous_scale=pal['seq'])
        render_card("retention", "Department Moves per Employee", fig,
                    description="How many department records per employee (proxy for transfers).",
                    insights=["Internal mobility health."],
                    recs=["Advertise internal roles; simplify transfer policy."])

# =============================== ROUTER ===============================
if st.session_state.page == "Overview":
    render_overview()
elif st.session_state.page == "Demographics":
    render_demographics()
elif st.session_state.page == "Salaries":
    render_salaries()
elif st.session_state.page == "Promotions":
    render_promotions()
elif st.session_state.page == "Retention":
    render_retention()

st.success("Render complete. Use the top buttons to navigate pages.")
