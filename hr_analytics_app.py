import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ========================== PAGE SETUP ==========================
st.set_page_config(page_title="HR Analytics Dashboard", layout="wide")

# -------------------------- THEME & NAVIGATION ------------------------
with st.sidebar:
    st.markdown("## ⚙ Settings")
    dark = st.toggle("🌗 Dark Mode", value=True)
    st.markdown("**Navigation:**")
    pages = ["👤 Demographics", "💵 Salaries", "🚀 Promotions", "🧲 Retention"]
    page_choice = st.radio("Go to Page:", pages)
    st.markdown("*Use this panel to toggle dark mode and quickly navigate between pages.*")

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
        df = df.copy(); df[sort_col] = pd.Timestamp("1970-01-01")
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

    for df, cols in [
        (salary, ["from_date","to_date"]),
        (dept_emp,["from_date","to_date"]),
        (title,   ["from_date","to_date"]),
        (employee,["birth_date","hire_date","termination_date"]),
    ]:
        for c in cols:
            if c in df.columns: df[c] = to_dt(df[c])

    emp = employee.rename(columns={"id":"employee_id"}).copy()
    emp["age"] = datetime.now().year - emp["birth_date"].dt.year if "birth_date" in emp.columns else np.nan
    emp["company_tenure"] = (pd.Timestamp.today() - emp["hire_date"]).dt.days/365.25 if "hire_date" in emp.columns else np.nan

    d_latest = latest_per_emp(dept_emp, "to_date" if "to_date" in dept_emp.columns else "from_date").merge(dept, on="dept_id", how="left")[["employee_id","dept_name"]] if {"employee_id","dept_id"}.issubset(dept_emp.columns) else snap[[c for c in ["employee_id","dept_name"] if c in snap.columns]].drop_duplicates()
    t_latest = latest_per_emp(title, "to_date" if "to_date" in title.columns else "from_date")[['employee_id','title']] if {"employee_id","title"}.issubset(title.columns) else snap[[c for c in ["employee_id","title"] if c in snap.columns]].drop_duplicates()
    s_latest = latest_per_emp(salary, "from_date")[['employee_id','amount']].rename(columns={'amount':'latest_salary'}) if {"employee_id","amount"}.issubset(salary.columns) else pd.DataFrame(columns=["employee_id","latest_salary"])

    snapshot = emp.merge(d_latest, on="employee_id", how="left")\
                  .merge(t_latest, on="employee_id", how="left")\
                  .merge(s_latest, on="employee_id", how="left")

    extras = [c for c in snap.columns if c not in snapshot.columns and c != 'employee_id']
    if extras: snapshot = snapshot.merge(snap[["employee_id"]+extras], on="employee_id", how="left")
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
tabs = ["👤 Demographics", "💵 Salaries", "🚀 Promotions", "🧲 Retention"]
tab_selection = tabs.index(page_choice)
d1, d2, d3, d4 = st.tabs(tabs)

# ========================= DEMOGRAPHICS ====================
if tab_selection==0:
    # [Add your 8 demographics charts here exactly as in your original code]
    pass  # keep your original code for demographics

# ==================== SALARIES & COMPENSATION =================
if tab_selection==1:
    # [Add your 8 salary charts here exactly as in your original code]
    pass

# ================= PROMOTIONS & CAREER GROWTH ================
if tab_selection==2:
    # [Add your 7 promotion charts here exactly as in your original code]
    pass

# ======================= RETENTION & TURNOVER ================
if tab_selection==3:
    pal = PALETTES['ret']
    if 'company_tenure' in snapshot.columns:
        fig = px.histogram(snapshot.dropna(subset=['company_tenure']), x='company_tenure', nbins=40, color_discrete_sequence=[pal['primary']])
        card("📊 Tenure Distribution (Years)", fig,
             desc="Histogram of time in company.",
             insights=["Heavy early churn or long‑tenured core."],
             recs=["Onboarding & mentorship to reduce early exits."])
    # ... باقي الرسوم البيانية
    # Retention by hire cohort final chart
    if 'hire_date' in employee.columns:
        e = employee.rename(columns={'id':'employee_id'})[['employee_id','hire_date','termination_date']]
        e['cohort'] = to_dt(e['hire_date']).dt.year
        e['end'] = pd.to_datetime('today')
        e['left'] = ~e['termination_date'].isna()
        e['retained_1y'] = (~e['left']) | ((to_dt(e['termination_date']) - to_dt(e['hire_date'])).dt.days >= 365)
        g = e.groupby('cohort')['retained_1y'].mean().reset_index()
        g['retained_1y'] = g['retained_1y'] * 100
        fig = px.bar(g, x='cohort', y='retained_1y', color='retained_1y', color_continuous_scale=pal['seq'])
        card("📅 1-Year Retention by Hire Cohort", fig,
             desc="Percentage of employees from each hiring year retained for at least one year.",
             insights=["Improvement or decline in onboarding effectiveness over time."],
             recs=["Strengthen early engagement for low-retention cohorts."])
