import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# ========================== PAGE SETUP ==========================
st.set_page_config(page_title="HR Analytics Dashboard (Lite)", layout="wide")

# -------------------------- THEME SWITCH ------------------------
with st.sidebar:
    st.markdown("## ⚙ Settings")
    dark = st.toggle("🌗 Dark Mode", value=True)

PLOTLY_TEMPLATE = "plotly_dark" if dark else "plotly_white"
UI_TEXT = "#e5e7eb" if dark else "#0f172a"
UI_BG = "#0b1021" if dark else "#ffffff"
UI_PANEL = "#111827" if dark else "#f8fafc"

PALETTES = {
    "demo": {"seq": px.colors.sequential.Blues,  "primary": "#0284c7"},
    "pay":  {"seq": px.colors.sequential.Greens, "primary": "#16a34a"},
    "promo":{"seq": px.colors.sequential.Purples,"primary": "#7c3aed"},
    "ret":  {"seq": px.colors.sequential.OrRd,   "primary": "#f97316"},
}

st.markdown(f"""
<style>
  .stApp {{ background:{UI_BG}; color:{UI_TEXT}; }}
  .card {{ background:{UI_PANEL}; border-radius:16px; padding:1rem; margin-bottom:1rem; }}
  h1,h2,h3 {{ color:#cbd5e1 !important; }}
  .muted {{ opacity:.85; }}
</style>
""", unsafe_allow_html=True)

# ============================ HELPERS ===========================
def to_dt(s):
    return pd.to_datetime(s, errors="coerce")

@st.cache_data
def load_data():
    salary = pd.read_csv("salary.csv")
    employee = pd.read_csv("employee.csv")
    snap = pd.read_csv("current_employee_snapshot.csv")
    dept = pd.read_csv("department.csv")
    title = pd.read_csv("title.csv")

    for df, cols in [(salary, ["from_date","to_date"]),
                     (employee,["birth_date","hire_date","termination_date"]),
                     (title,["from_date","to_date"])]:
        for c in cols:
            if c in df.columns: df[c] = to_dt(df[c])

    emp = employee.copy()
    if "birth_date" in emp.columns:
        emp["age"] = datetime.now().year - emp["birth_date"].dt.year
    else: emp["age"] = np.nan
    if "hire_date" in emp.columns:
        emp["company_tenure"] = (pd.Timestamp.today() - emp["hire_date"]).dt.days/365.25
    else: emp["company_tenure"] = np.nan

    latest_sal = salary.sort_values(['employee_id','from_date']).groupby('employee_id').tail(1)
    snapshot = emp.merge(latest_sal[['employee_id','amount']], on='employee_id', how='left')
    snapshot.rename(columns={'amount':'latest_salary'}, inplace=True)
    if 'dept_name' not in snapshot.columns: snapshot['dept_name'] = np.nan
    if 'title' not in snapshot.columns: snapshot['title'] = np.nan
    return salary, employee, snapshot, title

salary, employee, snapshot, title = load_data()

def card(title:str, fig=None, table=None):
    st.markdown(f"<div class='card'><h3>{title}</h3>", unsafe_allow_html=True)
    if fig is not None: st.plotly_chart(fig, use_container_width=True)
    if table is not None: st.dataframe(table, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ============================ HEADER ===========================
st.markdown("<h1 style='text-align:center;'>📊 HR Analytics Dashboard (Lite)</h1>", unsafe_allow_html=True)
st.markdown("---")

# ============================== TABS ===========================
d1,d2,d3,d4 = st.tabs(["👤 Demographics","💵 Salaries","🚀 Promotions","🧲 Retention"])

# ========================= DEMOGRAPHICS ====================
with d1:
    pal = PALETTES['demo']
    if 'age' in snapshot.columns:
        fig = px.histogram(snapshot.dropna(subset=['age']), x='age', nbins=40, color_discrete_sequence=[pal['primary']])
        card("🎂 Age Distribution", fig)
    if 'dept_name' in snapshot.columns:
        dep = snapshot['dept_name'].value_counts().reset_index(); dep.columns=['Department','Headcount']
        fig = px.bar(dep, x='Department', y='Headcount', color='Headcount', color_continuous_scale=pal['seq'])
        card("👥 Headcount by Department", fig)
    gcol = next((c for c in ["gender","sex"] if c in snapshot.columns), None)
    if gcol:
        overall = snapshot[gcol].value_counts().reset_index(); overall.columns=['Gender','Count']
        fig = px.pie(overall, names='Gender', values='Count')
        card("🚻 Gender Mix (Overall)", fig)
    if {'age','company_tenure'}.issubset(snapshot.columns):
        fig = px.density_heatmap(snapshot.dropna(subset=['age','company_tenure']), x='age', y='company_tenure', nbinsx=20, nbinsy=20, color_continuous_scale=pal['seq'])
        card("🔥 Age × Tenure (Heatmap)", fig)
    if {'age','dept_name'}.issubset(snapshot.columns):
        tmp = snapshot.copy(); tmp['age_group'] = pd.cut(tmp['age'], [10,20,30,40,50,60,70], labels=['10s','20s','30s','40s','50s','60s'])
        pivot = tmp.pivot_table(index='dept_name', columns='age_group', values='employee_id', aggfunc='count', fill_value=0).reset_index()
        fig = px.bar(pivot, x='dept_name', y=pivot.columns[1:], barmode='stack', color_discrete_sequence=pal['seq'])
        card("🏢 Age Group by Department", fig)

# ==================== SALARIES ==================
with d2:
    pal = PALETTES['pay']
    if {'employee_id','amount','from_date'}.issubset(salary.columns):
        s = salary.copy(); s['year'] = s['from_date'].dt.year
        avg = s.groupby('year')['amount'].mean().reset_index()
        fig = px.line(avg, x='year', y='amount', markers=True)
        card("📈 Average Salary Over Time", fig)
    top = salary.groupby('employee_id')['amount'].max().sort_values(ascending=False).head(20).reset_index(); top.columns=['Employee ID','Top Salary']
    card("💰 Top 20 Salaries (Table)", table=top)
    latest_sal = salary.sort_values(['employee_id','from_date']).groupby('employee_id').tail(1)
    fig = px.histogram(latest_sal, x='amount', nbins=40, color_discrete_sequence=[pal['primary']])
    card("📦 Salary Distribution (Latest)", fig)
    if 'dept_name' in snapshot.columns:
        m = snapshot[['employee_id','dept_name']].merge(latest_sal[['employee_id','amount']], on='employee_id', how='left').dropna()
        g = m.groupby('dept_name')['amount'].mean().reset_index().sort_values('amount', ascending=False)
        fig = px.bar(g, x='dept_name', y='amount', color='a_
