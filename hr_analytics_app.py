import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# ========================== PAGE SETUP ==========================
st.set_page_config(page_title="HR Analytics Dashboard (Light)", layout="wide")

# ======================== LOAD DATA (LIGHT) ====================
@st.cache_data
def load_light_data():
    # قراءة أول 50 صف فقط لتجنب استهلاك الذاكرة
    salary = pd.read_csv("salary.csv", nrows=50)
    employee = pd.read_csv("employee.csv", nrows=50)
    snapshot = pd.read_csv("current_employee_snapshot.csv", nrows=50)
    return salary, employee, snapshot

salary, employee, snapshot = load_light_data()

# ============================ SIDEBAR ===========================
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Demographics", "Salaries", "Promotions", "Retention"])

# ============================ HELPERS ===========================
def to_dt(s):
    return pd.to_datetime(s, errors="coerce")

def card(title, fig, desc=""):
    st.subheader(title)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    if desc:
        st.write(desc)
    st.markdown("---")

# ============================ PAGES =============================

# ---------- Demographics ----------
if page == "Demographics":
    if 'age' in snapshot.columns:
        df = snapshot.dropna(subset=['age'])
        fig = px.histogram(df, x='age', nbins=10, title="Age Distribution")
        card("🎂 Age Distribution", fig, "Histogram of employee ages.")

# ---------- Salaries ----------
elif page == "Salaries":
    if {'employee_id','amount'}.issubset(salary.columns):
        fig = px.histogram(salary, x='amount', nbins=10, title="Salary Distribution")
        card("💰 Salary Distribution", fig, "Histogram of latest salaries.")

# ---------- Promotions ----------
elif page == "Promotions":
    if {'employee_id','title','from_date'}.issubset(snapshot.columns):
        df = snapshot.dropna(subset=['from_date'])
        df['year'] = to_dt(df['from_date']).dt.year
        promotions_per_year = df.groupby('year').size().reset_index(name='Promotions')
        fig = px.bar(promotions_per_year, x='year', y='Promotions', title="Promotions per Year")
        card("📅 Promotions per Year", fig, "Count of promotions by year.")

# ---------- Retention ----------
elif page == "Retention":
    if 'hire_date' in snapshot.columns:
        snapshot['hire_date'] = to_dt(snapshot['hire_date'])
        snapshot['tenure_years'] = (pd.Timestamp.today() - snapshot['hire_date']).dt.days/365.25
        fig = px.histogram(snapshot, x='tenure_years', nbins=10, title="Tenure Distribution")
        card("📊 Tenure Distribution", fig, "Histogram of tenure in company.")
