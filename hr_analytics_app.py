import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# ========================== PAGE SETUP ==========================
st.set_page_config(page_title="HR Analytics Dashboard", layout="wide")

# ========================== THEME SWITCH =======================
with st.sidebar:
    st.markdown("## ⚙ Settings")
    dark = st.toggle("🌗 Dark Mode", value=True)

PLOTLY_TEMPLATE = "plotly_dark" if dark else "plotly_white"

PALETTES = {
    "demo": {"seq": px.colors.sequential.Blues,  "primary": "#0284c7"},
    "pay":  {"seq": px.colors.sequential.Greens, "primary": "#16a34a"},
    "promo":{"seq": px.colors.sequential.Purples,"primary": "#7c3aed"},
    "ret":  {"seq": px.colors.sequential.OrRd,   "primary": "#f97316"},
}

# ============================ HELPERS ==========================
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

def card(title: str, fig=None, table: pd.DataFrame|None=None):
    st.markdown(f"### {title}")
    if fig is not None:
        st.plotly_chart(fig_style(fig), use_container_width=True)
    if table is not None:
        st.dataframe(table, use_container_width=True)

# ======================== LOAD DATA ===========================
@st.cache_data
def load_data():
    # تأكدي أن الملفات موجودة بنفس المسار
    salary = pd.read_csv("salary.csv")
    employee = pd.read_csv("employee.csv")
    snapshot = employee.copy()
    if "birth_date" in snapshot.columns:
        snapshot["age"] = datetime.now().year - pd.to_datetime(snapshot["birth_date"], errors="coerce").dt.year
    else:
        snapshot["age"] = np.nan
    if "hire_date" in snapshot.columns:
        snapshot["company_tenure"] = (pd.Timestamp.today() - pd.to_datetime(snapshot["hire_date"], errors="coerce")).dt.days/365.25
    else:
        snapshot["company_tenure"] = np.nan
    return salary, employee, snapshot

salary, employee, snapshot = load_data()

# ============================ SIDEBAR FILTERS ==========================
st.sidebar.markdown("## Filters for Demographics")
show_age_hist = st.sidebar.checkbox("Age Distribution", value=True)
show_gender = st.sidebar.checkbox("Gender Mix", value=True)

st.sidebar.markdown("## Filters for Salaries")
show_salary_dist = st.sidebar.checkbox("Salary Distribution", value=True)
show_avg_salary_dept = st.sidebar.checkbox("Average Salary by Department", value=True)

# ============================ HEADER ==========================
st.markdown("# 📊 HR Analytics Dashboard")
st.markdown("Interactive charts across Demographics, Salaries, Promotions, and Retention.")
st.markdown("---")

# ============================ TABS ==========================
tab1, tab2 = st.tabs(["👤 Demographics", "💵 Salaries & Compensation"])

# ============================ DEMOGRAPHICS ==========================
with tab1:
    pal = PALETTES['demo']
    if show_age_hist and 'age' in snapshot.columns:
        fig = px.histogram(snapshot.dropna(subset=['age']), x='age', nbins=40, color_discrete_sequence=[pal['primary']])
        card("🎂 Age Distribution", fig)

    if show_gender and 'gender' in snapshot.columns:
        gen = snapshot['gender'].value_counts().reset_index()
        gen.columns = ['gender','count']
        fig = px.pie(gen, names='gender', values='count', color_discrete_sequence=pal['seq'])
        card("🚻 Gender Mix", fig)

# ============================ SALARIES ==========================
with tab2:
    pal = PALETTES['pay']
    if show_salary_dist and 'amount' in salary.columns:
        latest_sal = latest_per_emp(salary, 'from_date')
        fig = px.histogram(latest_sal, x='amount', nbins=40, color_discrete_sequence=[pal['primary']])
        card("💰 Salary Distribution (Latest)", fig)

    if show_avg_salary_dept and 'amount' in salary.columns:
        latest_sal = latest_per_emp(salary, 'from_date')
        # افترض أنه يوجد عمود dept_name في salary أو employee
        if 'dept_name' in snapshot.columns:
            m = snapshot[['employee_id','dept_name']].merge(latest_sal[['employee_id','amount']], on='employee_id', how='left').dropna()
            g = m.groupby('dept_name')['amount'].mean().reset_index()
            fig = px.bar(g, x='dept_name', y='amount', color='amount', color_continuous_scale=pal['seq'])
            fig.update_xaxes(tickangle=45)
            card("🏢 Average Salary by Department", fig)
