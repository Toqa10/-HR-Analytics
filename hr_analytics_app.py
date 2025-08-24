import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# ========================== PAGE SETUP ==========================
st.set_page_config(page_title="HR Analytics Dashboard", layout="wide")

# ========================== THEME ==============================
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

# ======================== LOAD & PREP DATA =====================
@st.cache_data
def load_data():
    salary = pd.read_csv("salary.csv")
    employee = pd.read_csv("employee.csv")
    snap = pd.read_csv("current_employee_snapshot.csv")
    dept = pd.read_csv("department.csv")
    dept_emp = pd.read_csv("department_employee.csv")
    dept_mgr = pd.read_csv("department_manager.csv")
    title = pd.read_csv("title.csv")

    # Dates parsing
    for df, cols in [
        (salary, ["from_date","to_date"]),
        (dept_emp,["from_date","to_date"]),
        (title,   ["from_date","to_date"]),
        (employee,["birth_date","hire_date"]),
    ]:
        for c in cols:
            if c in df.columns: df[c] = to_dt(df[c])

    # Base snapshot
    emp = employee.rename(columns={"id":"employee_id"}).copy()
    if "birth_date" in emp.columns:
        emp["age"] = datetime.now().year - emp["birth_date"].dt.year
    else:
        emp["age"] = np.nan
    if "hire_date" in emp.columns:
        emp["company_tenure"] = (pd.Timestamp.today() - emp["hire_date"]).dt.days/365.25
    else:
        emp["company_tenure"] = np.nan

    # Latest dept/title/salary
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
    return salary, employee, snapshot, dept_emp, dept, dept_mgr, title

salary, employee, snapshot, dept_emp, dept, dept_mgr, title = load_data()

# ============================ HEADER ===========================
st.markdown("""<h1 style='text-align:center;'>📊 HR Analytics Dashboard</h1>
<p style='text-align:center;' class='muted'>Interactive charts across Demographics, Salaries, Promotions, and Retention.</p>
""", unsafe_allow_html=True)
st.markdown("---")

# ============================ NAVIGATION ========================
page = st.sidebar.radio("Navigate Pages", ["Demographics","Salaries","Promotions","Retention"])

# ============================ DEMOGRAPHICS =======================
if page == "Demographics":
    pal = PALETTES['demo']
    # Sidebar filter
    demo_charts = st.sidebar.multiselect("Select Demographics charts to show:",
                                         ["Age Distribution","Age by Dept","Headcount by Dept","Top Titles","Age by Dept (Box)","Gender Mix","Gender by Dept","Age x Tenure Heatmap"],
                                         default=["Age Distribution","Age by Dept","Headcount by Dept","Top Titles","Age by Dept (Box)","Gender Mix","Gender by Dept","Age x Tenure Heatmap"])
    if "Age Distribution" in demo_charts:
        df = snapshot.dropna(subset=['age'])
        fig = px.histogram(df, x='age', nbins=40, color_discrete_sequence=[pal['primary']])
        card("🎂 Age Distribution", fig)

    if "Age by Dept" in demo_charts:
        if {'age','dept_name'}.issubset(snapshot.columns):
            tmp = snapshot.copy(); tmp['age_group'] = pd.cut(tmp['age'], [10,20,30,40,50,60,70], labels=['10s','20s','30s','40s','50s','60s'], right=False)
            pivot = tmp.pivot_table(index='dept_name', columns='age_group', values='employee_id', aggfunc='count', fill_value=0).reset_index()
            fig = px.bar(pivot, x='dept_name', y=pivot.columns[1:], barmode='stack', color_discrete_sequence=pal['seq'])
            fig.update_xaxes(tickangle=45)
            card("🏢 Age Group by Department", fig)

# ============================ SALARIES ============================
if page == "Salaries":
    pal = PALETTES['pay']
    salary_charts = st.sidebar.multiselect("Select Salary charts to show:",
                                           ["Average Salary","Top Salaries","Salary Distribution","Salary by Dept","Tenure vs Salary","Salary Growth","Salary Spread","Salary by Title"],
                                           default=["Average Salary","Top Salaries","Salary Distribution","Salary by Dept","Tenure vs Salary","Salary Growth","Salary Spread","Salary by Title"])
    if "Average Salary" in salary_charts:
        s = salary.copy(); s['from_date'] = to_dt(s['from_date']); s['year'] = s['from_date'].dt.year
        avg = s.groupby('year')['amount'].mean().reset_index()
        fig = px.line(avg, x='year', y='amount', markers=True)
        card("📈 Average Salary Over Time", fig)

# ============================ PROMOTIONS ==========================
if page == "Promotions":
    pal = PALETTES['promo']
    promo_charts = st.sidebar.multiselect("Select Promotion charts to show:",
                                          ["Promotions per Year","Time to First Promotion","Promotions by Dept","Top Multi-Promotion","Promotions by Gender","Career Path Length","Promotion Heatmap"],
                                          default=["Promotions per Year","Time to First Promotion","Promotions by Dept","Top Multi-Promotion","Promotions by Gender","Career Path Length","Promotion Heatmap"])
    if "Promotions per Year" in promo_charts:
        tdf = title.copy(); tdf['from_date'] = to_dt(tdf['from_date'])
        tdf = tdf.sort_values(['employee_id','from_date'])
        tdf['prev_title'] = tdf.groupby('employee_id')['title'].shift()
        tdf['changed'] = (tdf['title'] != tdf['prev_title']).astype(int)
        tdf['year'] = tdf['from_date'].dt.year
        per_year = tdf[tdf['changed']==1].groupby('year').size().reset_index(name='Promotions')
        fig = px.bar(per_year, x='year', y='Promotions', color='Promotions', color_continuous_scale=pal['seq'])
        card("📅 Promotions per Year", fig)

# ============================ RETENTION ==========================
if page == "Retention":
    pal = PALETTES['ret']
    retention_charts = st.sidebar.multiselect("Select Retention charts to show:",
                                              ["Tenure Distribution","Tenure by Dept","Headcount Over Time","Turnover Rate","Attrition by Tenure","Attrition by Dept","Retention by Cohort"],
                                              default=["Tenure Distribution","Tenure by Dept","Headcount Over Time","Turnover Rate","Attrition by Tenure","Attrition by Dept","Retention by Cohort"])
    if "Tenure Distribution" in retention_charts:
        fig = px.histogram(snapshot.dropna(subset=['company_tenure']), x='company_tenure', nbins=40, color_discrete_sequence=[pal['primary']])
        card("📊 Tenure Distribution (Years)", fig)
