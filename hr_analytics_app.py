import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# ========================== PAGE SETUP ==========================
st.set_page_config(page_title="HR Analytics Dashboard", layout="wide")

# -------------------------- THEME SWITCH ------------------------
with st.sidebar:
    st.markdown("## ⚙ Settings")
    dark = st.toggle("🌗 Dark Mode", value=True)

PLOTLY_TEMPLATE = "plotly_dark" if dark else "plotly_white"
UI_TEXT = "#e5e7eb" if dark else "#0f172a"
UI_BG = "#0b1021" if dark else "#ffffff"
UI_PANEL = "#111827" if dark else "#f8fafc"

PALETTES = {
    "demo": {"seq": px.colors.sequential.Blues,  "primary": "#0284c7", "accent": "#06b6d4"},
    "pay":  {"seq": px.colors.sequential.Greens, "primary": "#16a34a", "accent": "#84cc16"},
    "promo":{"seq": px.colors.sequential.Purples,"primary": "#7c3aed", "accent": "#ec4899"},
    "ret":  {"seq": px.colors.sequential.OrRd,   "primary": "#f97316", "accent": "#ef4444"},
}

st.markdown(f"""
<style>
  .stApp {{ background:{UI_BG}; color:{UI_TEXT}; }}
  .card {{ background:{UI_PANEL}; border-radius:16px; padding:1rem; margin-bottom:1rem; }}
  h1,h2,h3 {{ color:#cbd5e1 !important; }}
  .muted {{ opacity:.85; }}
  .notes b {{ color:#cbd5e1; }}
</style>
""", unsafe_allow_html=True)

# ============================ HELPERS ===========================
def to_dt(s):
    return pd.to_datetime(s, errors="coerce")

@st.cache_data
def latest_per_emp(df, sort_col):
    if sort_col not in df.columns:
        df = df.copy()
        df[sort_col] = pd.Timestamp("1970-01-01")
    return df.sort_values(["employee_id", sort_col]).groupby("employee_id", as_index=False).tail(1)

def fig_style(fig, title=None):
    fig.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    if title:
        fig.update_layout(title=dict(text=title, x=0.02, xanchor="left"))
    return fig

def card(title: str, fig=None, table: pd.DataFrame|None=None, desc:str="", insights:list[str]|None=None, recs:list[str]|None=None):
    st.markdown(f"<div class='card'><h3>{title}</h3>", unsafe_allow_html=True)
    if fig is not None:
        st.plotly_chart(fig_style(fig), use_container_width=True)
    if table is not None:
        st.dataframe(table, use_container_width=True)
    if desc or insights or recs:
        st.markdown("<div class='notes'>", unsafe_allow_html=True)
        if desc: st.markdown(f"*Description:* {desc}")
        if insights:
            st.markdown("*Insights:*")
            for i in insights: st.markdown(f"- {i}")
        if recs:
            st.markdown("*Recommendations:*")
            for r in recs: st.markdown(f"- {r}")
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ======================== LOAD & PREP DATA ======================
@st.cache_data
def load_data():
    salary = pd.read_csv("salary.csv")
    employee = pd.read_csv("employee.csv")
    snap = pd.read_csv("current_employee_snapshot.csv")
    dept = pd.read_csv("department.csv")
    dept_emp = pd.read_csv("department_employee.csv")
    dept_mgr = pd.read_csv("department_manager.csv")
    title = pd.read_csv("title.csv")

    # Convert dates
    for df, cols in [
        (salary, ["from_date","to_date"]),
        (dept_emp,["from_date","to_date"]),
        (title,   ["from_date","to_date"]),
        (employee,["birth_date","hire_date","termination_date"]),
    ]:
        for c in cols:
            if c in df.columns: df[c] = to_dt(df[c])

    # Base employee info
    emp = employee.rename(columns={"id":"employee_id"}).copy()
    emp["age"] = datetime.now().year - emp["birth_date"].dt.year if "birth_date" in emp.columns else np.nan
    emp["company_tenure"] = (pd.Timestamp.today() - emp["hire_date"]).dt.days/365.25 if "hire_date" in emp.columns else np.nan

    # Latest dept/title/salary
    if {"employee_id","dept_id"}.issubset(dept_emp.columns) and {"dept_id","dept_name"}.issubset(dept.columns):
        d_latest = latest_per_emp(dept_emp, "to_date").merge(dept, on="dept_id", how="left")[["employee_id","dept_name"]]
    else:
        d_latest = snap[[c for c in ["employee_id","dept_name"] if c in snap.columns]].drop_duplicates()

    t_latest = latest_per_emp(title, "to_date")[['employee_id','title']] if {"employee_id","title"}.issubset(title.columns) else snap[[c for c in ["employee_id","title"] if c in snap.columns]].drop_duplicates()
    s_latest = latest_per_emp(salary, "from_date")[['employee_id','amount']].rename(columns={'amount':'latest_salary'}) if {"employee_id","amount"}.issubset(salary.columns) else pd.DataFrame(columns=["employee_id","latest_salary"])

    snapshot = emp.merge(d_latest, on="employee_id", how="left")\
                  .merge(t_latest, on="employee_id", how="left")\
                  .merge(s_latest, on="employee_id", how="left")

    extras = [c for c in snap.columns if c not in snapshot.columns and c != 'employee_id']
    if extras:
        snapshot = snapshot.merge(snap[["employee_id"]+extras], on="employee_id", how="left")

    return salary, employee, snapshot, dept_emp, dept, dept_mgr, title

salary, employee, snapshot, dept_emp, dept, dept_mgr, title = load_data()
for col in ["dept_name","title","company_tenure","age","latest_salary"]:
    if col not in snapshot.columns: snapshot[col] = np.nan

# ============================ HEADER ===========================
st.markdown("""
<h1 style='text-align:center;'>📊 HR Analytics Dashboard</h1>
<p style='text-align:center;' class='muted'>30 interactive charts across Demographics, Salaries, Promotions, and Retention. Each chart includes Description, Insights, and Recommendations.</p>
""", unsafe_allow_html=True)
st.markdown("---")

# ============================== TABS ===========================
d1, d2, d3, d4 = st.tabs([
    "👤 Demographics (8)",
    "💵 Salaries & Compensation (8)",
    "🚀 Promotions & Career Growth (7)",
    "🧲 Retention & Turnover (7)",
])

# ========================= DEMOGRAPHICS (8) ====================
with d1:
    pal = PALETTES['demo']
    # Age histogram
    if 'age' in snapshot.columns:
        df = snapshot.dropna(subset=['age'])
        fig = px.histogram(df, x='age', nbins=40, color_discrete_sequence=[pal['primary']])
        card("🎂 Age Distribution", fig, desc="Histogram of employees' ages.", insights=["Highlights dominant age bands and outliers."], recs=["Tailor L&D and benefits by age clusters."])

    # Age groups by dept (stacked)
    if {'age','dept_name'}.issubset(snapshot.columns):
        tmp = snapshot.copy()
        tmp['age_group'] = pd.cut(tmp['age'], [10,20,30,40,50,60,70], labels=['10s','20s','30s','40s','50s','60s'], right=False)
        pivot = tmp.pivot_table(index='dept_name', columns='age_group', values='employee_id', aggfunc='count', fill_value=0).reset_index()
        fig = px.bar(pivot, x='dept_name', y=pivot.columns[1:], barmode='stack', color_discrete_sequence=pal['seq'])
        fig.update_xaxes(tickangle=45)
        card("🏢 Age Group Composition by Department", fig, desc="Stacked headcount by age group.", insights=["Detect departments with skewed demographics."], recs=["Balance hiring to reduce succession risk."])

    # Headcount by dept
    if 'dept_name' in snapshot.columns:
        dep = snapshot['dept_name'].value_counts().reset_index()
        dep.columns = ['Department','Headcount']
        fig = px.bar(dep, x='Department', y='Headcount', color='Headcount', color_continuous_scale=pal['seq'])
        card("👥 Headcount by Department", fig, desc="Current headcount per department.", insights=["Capacity hotspots and understaffed teams."], recs=["Align hiring with demand and revenue impact."])

    # Title headcount Top 20
    if 'title' in snapshot.columns:
        t = snapshot['title'].fillna('Unknown').value_counts().head(20).reset_index()
        t.columns = ['Title','Headcount']
        fig = px.bar(t, x='Title', y='Headcount', color='Headcount', color_continuous_scale=pal['seq'])
        fig.update_xaxes(tickangle=45)
        card("🏷 Top 20 Titles by Headcount", fig, desc="Most common roles.", insights=["Identify critical roles and single points of failure."], recs=["Cross-train & succession planning for critical titles."])

    # Age by dept (box)
    if {'age','dept_name'}.issubset(snapshot.columns):
        fig = px.box(snapshot.dropna(subset=['age','dept_name']), x='dept_name', y='age', color='dept_name')
        fig.update_xaxes(tickangle=45, title="")
        card("📦 Age by Department (Box)", fig, desc="Spread & median age by department.", insights=["Outliers suggest tailored wellbeing programs."], recs=["Review workload design in teams with wide age spread."])

    # Gender overall + by dept
    gcol = next((c for c in ["gender","sex","Gender","Sex"] if c in snapshot.columns), None)
    if gcol:
        overall = snapshot[gcol].value_counts().reset_index(); overall.columns=['Gender','Count']
        fig = px.pie(overall, names='Gender', values='Count')
        card("🚻 Gender Mix (Overall)", fig, desc="Gender composition company-wide.", insights=["Imbalances vs targets."], recs=["Expand sourcing & ensure unbiased screening."])
        if 'dept_name' in snapshot.columns:
            gdept = snapshot[[gcol,'dept_name']].dropna().value_counts().reset_index(name='Count').rename(columns={gcol:'Gender'})
            fig = px.bar(gdept, x='dept_name', y='Count', color='Gender', barmode='stack')
            card("🚻 Gender Ratio by Department", fig, desc="Gender distribution per department.", insights=["Surfacing most skewed units."], recs=["Local goals & mentorship for underrepresented groups."])

    # Age vs Tenure heatmap
    if {'age','company_tenure'}.issubset(snapshot.columns):
        fig = px.density_heatmap(snapshot.dropna(subset=['age','company_tenure']), x='age', y='company_tenure', nbinsx=20, nbinsy=20, color_continuous_scale=pal['seq'])
        card("🔥 Age × Tenure (Heat)", fig, desc="Density across age and tenure.", insights=["Clusters reveal career stage concentrations."], recs=["Design stage‑specific L&D and retention programs."])

# ==================== SALARIES & COMPENSATION (8) =================
with d2:
    pal = PALETTES['pay']
    latest_sal = latest_per_emp(salary, 'from_date') if {'employee_id','amount'}.issubset(salary.columns) else None

    # Average salary per year
    if {'employee_id','amount','from_date'}.issubset(salary.columns):
        s = salary.copy(); s['from_date'] = to_dt(s['from_date']); s['year'] = s['from_date'].dt.year
        avg = s.groupby('year')['amount'].mean().reset_index()
        fig = px.line(avg, x='year', y='amount', markers=True)
        card("📈 Average Salary Over Time", fig, desc="Year‑over‑year average compensation.", insights=["Acceleration or stagnation in pay growth."], recs=["Budget merit increases aligned with market."])

    # Top 20 salaries
    if {'employee_id','amount'}.issubset(salary.columns):
        top = salary.groupby('employee_id')['amount'].max().sort_values(ascending=False).head(20).reset_index()
        top.columns = ['Employee ID','Top Salary']
        card("💰 Top 20 Salaries (Table)", None, top.style.format({'Top Salary':'{:,.0f}'}).data, desc="Highest recorded salary per employee.", insights=["Executive bands and outliers."], recs=["Ensure pay governance & internal parity."])

    # Salary histogram (latest)
    if latest_sal is not None:
        fig = px.histogram(latest_sal, x='amount', nbins=40, color_discrete_sequence=[pal['primary']])
        card("📦 Salary Distribution (Latest)", fig, desc="Histogram of latest salary amounts.", insights=["Skewness; band compression or outliers."], recs=["Review ranges; consider mid‑point corrections."])

    # Average salary by department
    if latest_sal is not None and 'dept_name' in snapshot.columns:
        m = snapshot[['employee_id','dept_name']].merge(latest_sal[['employee_id','amount']], on='employee_id', how='left').dropna()
        g = m.groupby('dept_name')['amount'].mean().reset_index().sort_values('amount', ascending=False)
        fig = px.bar(g, x='dept_name', y='amount', color='amount', color_continuous_scale=pal['seq'])
        fig.update_xaxes(tickangle=45)
        card("🏢 Average Salary by Department", fig, desc="Mean latest compensation per department.", insights=["High‑paying functions vs support units."], recs=["Benchmark vs market; adjust critical roles."])

# ================= PROMOTIONS & CAREER GROWTH (7) =================
with d3:
    pal = PALETTES['promo']
    promos_ready = {"employee_id","title","from_date"}.issubset(title.columns)

    if promos_ready:
        tdf = title.copy(); tdf['from_date'] = to_dt(tdf['from_date'])
        tdf = tdf.sort_values(['employee_id','from_date'])
        tdf['prev_title'] = tdf.groupby('employee_id')['title'].shift()
        tdf['changed'] = (tdf['title'] != tdf['prev_title']).fillna(False)
        # Count promotions
        promo_counts = tdf[tdf['changed']].groupby('title').size().reset_index(name='Promotions').sort_values('Promotions',ascending=False).head(20)
        fig = px.bar(promo_counts, x='title', y='Promotions', color='Promotions', color_continuous_scale=pal['seq'])
        fig.update_xaxes(tickangle=45)
        card("🚀 Top 20 Promoted Titles", fig, desc="Titles with most upward movements.", insights=["Identify promotion bottlenecks."], recs=["Career planning focus on high churn roles."])

# ====================== RETENTION & TURNOVER (7) =================
with d4:
    pal = PALETTES['ret']

    # Retention by hire cohort
    if 'hire_date' in employee.columns:
        e = employee.rename(columns={'id':'employee_id'})[['employee_id','hire_date','termination_date']].copy()
        e['hire_date'] = to_dt(e['hire_date'])
        e['termination_date'] = to_dt(e['termination_date'])
        e['cohort'] = e['hire_date'].dt.year
        e['left'] = ~e['termination_date'].isna()
        e['retained_1y'] = (~e['left']) | ((e['termination_date'] - e['hire_date']).dt.days >= 365)
        g = e.groupby('cohort')['retained_1y'].mean().reset_index()
        g['Retention%_1y'] = g['retained_1y']*100
        fig = px.bar(g, x='cohort', y='Retention%_1y', color='Retention%_1y', color_continuous_scale=pal['seq'])
        card("🛡 1‑Year Retention by Hire Cohort", fig,
             desc="Share of each hire cohort retained at least 1 year (approx).",
             insights=["Cohorts with weaker stickiness."],
             recs=["Double‑down on onboarding for weaker cohorts."])
