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

def fig_style(fig):
    fig.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
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

    # rename 'id' to 'employee_id'
    employee = employee.rename(columns={'id':'employee_id'})

    # basic age & tenure
    if 'birth_date' in employee.columns:
        employee['birth_date'] = pd.to_datetime(employee['birth_date'], errors='coerce')
        employee['age'] = datetime.now().year - employee['birth_date'].dt.year
    else:
        employee['age'] = np.nan

    if 'hire_date' in employee.columns:
        employee['hire_date'] = pd.to_datetime(employee['hire_date'], errors='coerce')
        employee['company_tenure'] = (pd.Timestamp.today() - employee['hire_date']).dt.days/365.25
    else:
        employee['company_tenure'] = np.nan

    return salary, employee

salary, employee = load_data()

# ============================ HEADER ============================
st.markdown("<h1 style='text-align:center;'>📊 HR Analytics Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;' class='muted'>All charts show automatically without filters.</p>", unsafe_allow_html=True)
st.markdown("---")

# ============================ TABS ==============================
pages = ["👤 Demographics", "💵 Salaries", "🚀 Promotions", "🧲 Retention"]
page = st.sidebar.radio("Go to Page", pages)

# ====================== DEMOGRAPHICS ============================
if page == "👤 Demographics":
    pal = PALETTES['demo']
    df = employee.dropna(subset=['age'])
    
    # Age Distribution
    fig1 = px.histogram(df, x='age', nbins=40, color_discrete_sequence=[pal['primary']])
    card("🎂 Age Distribution", fig1)
    
    # Headcount by Gender
    if 'gender' in df.columns:
        gen = df['gender'].value_counts().reset_index().rename(columns={'index':'gender','gender':'count'})
        fig2 = px.pie(gen, names='gender', values='count', color_discrete_sequence=pal['seq'])
        card("⚥ Gender Distribution", fig2)
    
    # Age vs Tenure Heatmap
    heat = df.pivot_table(index=pd.cut(df['age'], bins=10), 
                          columns=pd.cut(df['company_tenure'], bins=10), 
                          values='employee_id', aggfunc='count', fill_value=0)
    fig3 = px.imshow(heat, text_auto=True, color_continuous_scale=pal['seq'])
    card("🌡 Age x Tenure Heatmap", fig3)

# ========================= SALARIES =============================
if page == "💵 Salaries":
    pal = PALETTES['pay']
    if {'employee_id','amount'}.issubset(salary.columns):
        # Latest salary per employee
        latest_sal = salary.groupby('employee_id')['amount'].max().reset_index()
        fig1 = px.histogram(latest_sal, x='amount', nbins=40, color_discrete_sequence=[pal['primary']])
        card("💰 Salary Distribution", fig1)
        
        fig2 = px.bar(latest_sal.sort_values('amount', ascending=False).head(20), x='employee_id', y='amount', color_discrete_sequence=[pal['accent']])
        card("🏆 Top 20 Salaries", fig2)

# ========================= PROMOTIONS ===========================
if page == "🚀 Promotions":
    pal = PALETTES['promo']
    st.info("No promotion data available. Add 'title.csv' with employee promotions to visualize charts.")

# ========================= RETENTION ============================
if page == "🧲 Retention":
    pal = PALETTES['ret']
    if 'company_tenure' in employee.columns:
        fig1 = px.histogram(employee, x='company_tenure', nbins=40, color_discrete_sequence=[pal['primary']])
        card("📊 Tenure Distribution", fig1)
