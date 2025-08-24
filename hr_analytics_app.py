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

    # convert date columns
    for df, cols in [
        (salary, ["from_date","to_date"]),
        (dept_emp,["from_date","to_date"]),
        (title,   ["from_date","to_date"]),
        (employee,["birth_date","hire_date","termination_date"]),
    ]:
        for c in cols:
            if c in df.columns: df[c] = to_dt(df[c])

    # base employee
    emp = employee.rename(columns={"id":"employee_id"}).copy()
    if "birth_date" in emp.columns:
        emp["age"] = datetime.now().year - emp["birth_date"].dt.year
    else:
        emp["age"] = np.nan
    if "hire_date" in emp.columns:
        emp["company_tenure"] = (pd.Timestamp.today() - emp["hire_date"]).dt.days/365.25
    else:
        emp["company_tenure"] = np.nan

    # latest dept/title/salary
    if {"employee_id","dept_id"}.issubset(dept_emp.columns) and {"dept_id","dept_name"}.issubset(dept.columns):
        d_latest = latest_per_emp(dept_emp, "to_date" if "to_date" in dept_emp.columns else "from_date").merge(dept, on="dept_id", how="left")
        d_latest = d_latest[["employee_id","dept_name"]]
    else:
        d_latest = snap[[c for c in ["employee_id","dept_name"] if c in snap.columns]].drop_duplicates()

    if {"employee_id","title"}.issubset(title.columns):
        t_latest = latest_per_emp(title, "to_date" if "to_date" in title.columns else "from_date")[['employee_id','title']]
    else:
        t_latest = snap[[c for c in ["employee_id","title"] if c in snap.columns]].drop_duplicates()

    if {"employee_id","amount"}.issubset(salary.columns):
        s_latest = latest_per_emp(salary, "from_date")[['employee_id','amount']].rename(columns={'amount':'latest_salary'})
    else:
        s_latest = pd.DataFrame(columns=["employee_id","latest_salary"])

    snapshot = emp.merge(d_latest, on="employee_id", how="left")\
                  .merge(t_latest, on="employee_id", how="left")\
                  .merge(s_latest, on="employee_id", how="left")

    # extras from snapshot
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
<p style='text-align:center;' class='muted'>Interactive HR charts with filters. Toggle charts on/off.</p>
""", unsafe_allow_html=True)
st.markdown("---")

# ============================== SIDEBAR NAV ======================
pages = ["👤 Demographics","💵 Salaries","🚀 Promotions","🧲 Retention"]
page = st.sidebar.radio("Go to page", pages)

# ============================ DEMOGRAPHICS =======================
if page=="👤 Demographics":
    pal = PALETTES['demo']
    charts = st.sidebar.multiselect("Select charts to display:", [
        "Age Distribution","Age Group by Dept","Headcount by Dept","Top Titles",
        "Age by Dept","Gender Overall","Gender by Dept","Age x Tenure Heatmap"
    ], default=[
        "Age Distribution","Age Group by Dept","Headcount by Dept","Top Titles",
        "Age by Dept","Gender Overall","Gender by Dept","Age x Tenure Heatmap"
    ])

    if 'Age Distribution' in charts and 'age' in snapshot.columns:
        df = snapshot.dropna(subset=['age'])
        fig = px.histogram(df, x='age', nbins=40, color_discrete_sequence=[pal['primary']])
        card("🎂 Age Distribution", fig)

    if 'Age Group by Dept' in charts and {'age','dept_name'}.issubset(snapshot.columns):
        tmp = snapshot.copy(); tmp['age_group'] = pd.cut(tmp['age'], [10,20,30,40,50,60,70],
                                                          labels=['10s','20s','30s','40s','50s','60s'], right=False)
        pivot = tmp.pivot_table(index='dept_name', columns='age_group', values='employee_id', aggfunc='count', fill_value=0).reset_index()
        fig = px.bar(pivot, x='dept_name', y=pivot.columns[1:], barmode='stack', color_discrete_sequence=pal['seq'])
        fig.update_xaxes(tickangle=45)
        card("🏢 Age Group Composition by Department", fig)

    if 'Headcount by Dept' in charts and 'dept_name' in snapshot.columns:
        dep = snapshot['dept_name'].value_counts().reset_index()
        dep.columns = ['Department','Headcount']
        fig = px.bar(dep, x='Department', y='Headcount', color='Headcount', color_continuous_scale=pal['seq'])
        card("👥 Headcount by Department", fig)

    if 'Top Titles' in charts and 'title' in snapshot.columns:
        t = snapshot['title'].fillna('Unknown').value_counts().head(20).reset_index()
        t.columns = ['Title','Headcount']
        fig = px.bar(t, x='Title', y='Headcount', color='Headcount', color_continuous_scale=pal['seq'])
        fig.update_xaxes(tickangle=45)
        card("🏷 Top Titles", fig)

    if 'Age by Dept' in charts and {'age','dept_name'}.issubset(snapshot.columns):
        fig = px.box(snapshot.dropna(subset=['age','dept_name']), x='dept_name', y='age', color='dept_name')
        fig.update_xaxes(tickangle=45)
        card("📦 Age by Department", fig)

    gcol = next((c for c in ["gender","Gender","sex","Sex"] if c in snapshot.columns), None)
    if 'Gender Overall' in charts and gcol:
        overall = snapshot[gcol].value_counts().reset_index(); overall.columns=['Gender','Count']
        fig = px.pie(overall, names='Gender', values='Count', color_discrete_sequence=pal['seq'])
        card("🚻 Gender Mix (Overall)", fig)

    if 'Gender by Dept' in charts and gcol and 'dept_name' in snapshot.columns:
        gdept = snapshot[[gcol,'dept_name']].dropna().value_counts().reset_index(name='Count').rename(columns={gcol:'Gender'})
        fig = px.bar(gdept, x='dept_name', y='Count', color='Gender', barmode='stack')
        card("🚻 Gender Ratio by Department", fig)

    if 'Age x Tenure Heatmap' in charts and {'age','company_tenure'}.issubset(snapshot.columns
