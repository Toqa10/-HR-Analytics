import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# ========================== PAGE SETUP ==========================
st.set_page_config(page_title="HR Analytics Dashboard", layout="wide")

# -------------------------- SIDEBAR NAVIGATION ------------------------
with st.sidebar:
    st.markdown("## ⚙ Settings")
    dark = st.toggle("🌗 Dark Mode", value=True)
    page = st.selectbox("Navigate Dashboard:", ["Demographics","Salaries","Promotions","Retention"])

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
  .notes b {{ color:#cbd5e1; }}
</style>
""", unsafe_allow_html=True)

# ============================ HELPERS ===========================
def to_dt(s): return pd.to_datetime(s, errors="coerce")

@st.cache_data
def latest_per_emp(df, sort_col):
    if sort_col not in df.columns:
        df = df.copy(); df[sort_col] = pd.Timestamp("1970-01-01")
    return df.sort_values(["employee_id", sort_col]).groupby("employee_id", as_index=False).tail(1)

def fig_style(fig, title=None):
    fig.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    if title: fig.update_layout(title=dict(text=title, x=0.02, xanchor="left"))
    return fig

def card(title: str, fig=None, table: pd.DataFrame|None=None, desc:str="", insights:list[str]|None=None, recs:list[str]|None=None):
    st.markdown(f"<div class='card'><h3>{title}</h3>", unsafe_allow_html=True)
    if fig is not None: st.plotly_chart(fig_style(fig), use_container_width=True)
    if table is not None: st.dataframe(table, use_container_width=True)
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
    title = pd.read_csv("title.csv")
    dept = pd.read_csv("department.csv")
    dept_emp = pd.read_csv("department_employee.csv")
    
    for df, cols in [(salary, ["from_date","to_date"]), (dept_emp,["from_date","to_date"]), (title,["from_date","to_date"]), (employee,["birth_date","hire_date"])]:
        for c in cols:
            if c in df.columns: df[c] = to_dt(df[c])
            
    emp = employee.rename(columns={"id":"employee_id"}).copy()
    emp["age"] = datetime.now().year - emp["birth_date"].dt.year if "birth_date" in emp.columns else np.nan
    emp["company_tenure"] = (pd.Timestamp.today() - emp["hire_date"]).dt.days/365.25 if "hire_date" in emp.columns else np.nan
    
    d_latest = latest_per_emp(dept_emp, "to_date").merge(dept, on="dept_id", how="left")[["employee_id","dept_name"]] if {"employee_id","dept_id"}.issubset(dept_emp.columns) else emp[["employee_id"]]
    t_latest = latest_per_emp(title, "to_date")[['employee_id','title']] if {"employee_id","title"}.issubset(title.columns) else emp[["employee_id"]]
    s_latest = latest_per_emp(salary, "from_date")[['employee_id','amount']].rename(columns={'amount':'latest_salary'}) if {"employee_id","amount"}.issubset(salary.columns) else emp[["employee_id"]]
    
    snapshot = emp.merge(d_latest, on="employee_id", how="left").merge(t_latest, on="employee_id", how="left").merge(s_latest, on="employee_id", how="left")
    return salary, employee, snapshot, title, dept, dept_emp

salary, employee, snapshot, title, dept, dept_emp = load_data()
for col in ["dept_name","title","company_tenure","age","latest_salary"]:
    if col not in snapshot.columns: snapshot[col] = np.nan

st.markdown("<h1 style='text-align:center;'>📊 HR Analytics Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;' class='muted'>Interactive charts with Description, Insights, Recommendations.</p>", unsafe_allow_html=True)
st.markdown("---")

# ========================== PAGE DISPLAY ==========================
def show_demographics():
    pal = PALETTES['demo']
    options = st.multiselect("Select Charts to Show:", ["Age Distribution","Age by Dept","Headcount by Dept","Top Titles","Gender Mix","Age vs Tenure Heatmap"], default=None)
    
    if "Age Distribution" in options:
        df = snapshot.dropna(subset=['age'])
        fig = px.histogram(df, x='age', nbins=40, color_discrete_sequence=[pal['primary']])
        card("🎂 Age Distribution", fig, desc="Histogram of employees' ages.")
        
    if "Age by Dept" in options and {'age','dept_name'}.issubset(snapshot.columns):
        tmp = snapshot.copy(); tmp['age_group'] = pd.cut(tmp['age'], [10,20,30,40,50,60,70], labels=['10s','20s','30s','40s','50s','60s'], right=False)
        pivot = tmp.pivot_table(index='dept_name', columns='age_group', values='employee_id', aggfunc='count', fill_value=0).reset_index()
        fig = px.bar(pivot, x='dept_name', y=pivot.columns[1:], barmode='stack', color_discrete_sequence=pal['seq'])
        fig.update_xaxes(tickangle=45)
        card("🏢 Age Group by Dept", fig)

def show_salaries():
    pal = PALETTES['pay']
    options = st.multiselect("Select Charts to Show:", ["Avg Salary Over Time","Top 20 Salaries","Salary Distribution","Avg Salary by Dept"], default=None)
    
    if "Avg Salary Over Time" in options and {'employee_id','amount','from_date'}.issubset(salary.columns):
        s = salary.copy(); s['year'] = s['from_date'].dt.year
        avg = s.groupby('year')['amount'].mean().reset_index()
        fig = px.line(avg, x='year', y='amount', markers=True)
        card("📈 Avg Salary Over Time", fig)

def show_promotions():
    pal = PALETTES['promo']
    options = st.multiselect("Select Charts to Show:", ["Promotions per Year","Time to First Promotion","Promotions by Dept"], default=None)
    if {"employee_id","title","from_date"}.issubset(title.columns):
        tdf = title.copy().sort_values(['employee_id','from_date'])
        tdf['prev_title'] = tdf.groupby('employee_id')['title'].shift()
        tdf['changed'] = (tdf['title'] != tdf['prev_title']).astype(int)
        tdf['year'] = tdf['from_date'].dt.year
        promos = tdf.groupby('employee_id')['changed'].sum().reset_index(name='promotion_count')
        
        if "Promotions per Year" in options:
            per_year = tdf[tdf['changed']==1].groupby('year').size().reset_index(name='Promotions')
            fig = px.bar(per_year, x='year', y='Promotions', color='Promotions', color_continuous_scale=pal['seq'])
            card("📅 Promotions per Year", fig)

def show_retention():
    pal = PALETTES['ret']
    options = st.multiselect("Select Charts to Show:", ["Tenure Distribution","Attrition by Dept","1-Year Retention"], default=None)
    
    if "Tenure Distribution" in options and 'company_tenure' in snapshot.columns:
        fig = px.histogram(snapshot.dropna(subset=['company_tenure']), x='company_tenure', nbins=40, color_discrete_sequence=[pal['primary']])
        card("📊 Tenure Distribution", fig)

# ========================== RENDER PAGE ==========================
if page == "Demographics": show_demographics()
elif page == "Salaries": show_salaries()
elif page == "Promotions": show_promotions()
elif page == "Retention": show_retention()
