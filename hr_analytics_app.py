import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# ========================== PAGE SETUP ==========================
st.set_page_config(page_title="HR Analytics Dashboard Lite", layout="wide")

# -------------------------- THEME ------------------------
with st.sidebar:
    st.markdown("## ⚙ Settings")
    dark = st.toggle("🌗 Dark Mode", value=True)

PLOTLY_TEMPLATE = "plotly_dark" if dark else "plotly_white"
UI_TEXT = "#e5e7eb" if dark else "#0f172a"
UI_BG = "#0b1021" if dark else "#ffffff"
UI_PANEL = "#111827" if dark else "#f8fafc"

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

def card(title: str, fig=None, table: pd.DataFrame=None):
    st.markdown(f"<div class='card'><h3>{title}</h3>", unsafe_allow_html=True)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    if table is not None:
        st.dataframe(table, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ======================== LOAD & PREP DATA ======================
@st.cache_data
def load_data_sample():
    # Load first 500 rows only
    salary = pd.read_csv("salary.csv").head(500)
    employee = pd.read_csv("employee.csv").head(500)

    # Basic preprocessing
    if 'birth_date' in employee.columns:
        employee['age'] = datetime.now().year - to_dt(employee['birth_date']).dt.year
    else:
        employee['age'] = np.nan

    if 'hire_date' in employee.columns:
        employee['company_tenure'] = (pd.Timestamp.today() - to_dt(employee['hire_date'])).dt.days/365.25
    else:
        employee['company_tenure'] = np.nan

    return salary, employee

salary, employee = load_data_sample()

# ============================ HEADER ===========================
st.markdown("""
<h1 style='text-align:center;'>📊 HR Analytics Dashboard Lite</h1>
<p style='text-align:center;' class='muted'>Lightweight demo: Age & Salary distribution charts.</p>
""", unsafe_allow_html=True)
st.markdown("---")

# ======================== DEMOGRAPHICS ==========================
if 'age' in employee.columns:
    df_age = employee.dropna(subset=['age'])
    if not df_age.empty:
        fig_age = px.histogram(df_age, x='age', nbins=20, color_discrete_sequence=["#0284c7"], template=PLOTLY_TEMPLATE)
        card("🎂 Age Distribution", fig_age)

# ======================== SALARY DISTRIBUTION ===================
if {'employee_id','amount'}.issubset(salary.columns):
    fig_salary = px.histogram(salary, x='amount', nbins=20, color_discrete_sequence=["#16a34a"], template=PLOTLY_TEMPLATE)
    card("💰 Salary Distribution (Sample)", fig_salary)
