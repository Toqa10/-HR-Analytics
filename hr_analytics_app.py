import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# ========================== PAGE SETUP ==========================
st.set_page_config(page_title="HR Analytics Dashboard", layout="wide")

# ========================== LOAD DATA ===========================
@st.cache_data
def load_data():
    salary = pd.read_csv("salary.csv")
    employee = pd.read_csv("employee.csv")
    snap = pd.read_csv("current_employee_snapshot.csv")
    dept = pd.read_csv("department.csv")
    dept_emp = pd.read_csv("department_employee.csv")
    dept_mgr = pd.read_csv("department_manager.csv")
    title = pd.read_csv("title.csv")

    # تحويل التواريخ
    date_cols = {
        "salary": ["from_date","to_date"],
        "dept_emp":["from_date","to_date"],
        "title":["from_date","to_date"],
        "employee":["birth_date","hire_date","termination_date"]
    }

    for df_name, cols in date_cols.items():
        df = locals()[df_name]
        for c in cols:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors='coerce')

    # بيانات الموظفين الأساسية
    emp = employee.copy()
    emp["age"] = datetime.now().year - pd.to_datetime(emp["birth_date"], errors='coerce').dt.year
    emp["company_tenure"] = (pd.Timestamp.today() - pd.to_datetime(emp["hire_date"], errors='coerce')).dt.days/365.25

    # أحدث القسم
    if {"employee_id","dept_id"}.issubset(dept_emp.columns) and {"dept_id","dept_name"}.issubset(dept.columns):
        d_latest = dept_emp.sort_values(["employee_id","to_date"]).groupby("employee_id").tail(1).merge(dept, on="dept_id", how="left")[["employee_id","dept_name"]]
    else:
        d_latest = snap[["employee_id","dept_name"]].drop_duplicates()

    # أحدث الوظيفة
    if {"employee_id","title"}.issubset(title.columns):
        t_latest = title.sort_values(["employee_id","to_date"]).groupby("employee_id").tail(1)[["employee_id","title"]]
    else:
        t_latest = snap[["employee_id","title"]].drop_duplicates()

    # أحدث الراتب
    if {"employee_id","amount"}.issubset(salary.columns):
        s_latest = salary.sort_values(["employee_id","from_date"]).groupby("employee_id").tail(1)[['employee_id','amount']].rename(columns={'amount':'latest_salary'})
    else:
        s_latest = pd.DataFrame(columns=["employee_id","latest_salary"])

    snapshot = emp.merge(d_latest, on="employee_id", how="left")\
                  .merge(t_latest, on="employee_id", how="left")\
                  .merge(s_latest, on="employee_id", how="left")
    return snapshot

snapshot = load_data()

# ========================== HELPERS ===========================
def card(title: str, fig=None, table=None, desc="", insights=None, recs=None):
    st.markdown(f"<div style='background:#111827; border-radius:12px; padding:12px; margin-bottom:12px; color:#f1f5f9;'>", unsafe_allow_html=True)
    st.markdown(f"### {title}")
    if fig: st.plotly_chart(fig, use_container_width=True)
    if table is not None:
        st.dataframe(table)
        st.download_button("⬇ Download CSV", table.to_csv(index=False), file_name=f"{title.replace(' ','_')}.csv")
        if st.button(f"✨ Highlight Max ({title})"):
            col = table.columns[1] if len(table.columns)>1 else table.columns[0]
            st.markdown(f"**Max {col}: {table[col].max()}**")
    if desc: st.markdown(f"**Description:** {desc}")
    if insights:
        st.markdown("**Insights:**")
        for i in insights: st.markdown(f"- {i}")
    if recs:
        st.markdown("**Recommendations:**")
        for r in recs: st.markdown(f"- {r}")
    st.markdown("</div>", unsafe_allow_html=True)

# ========================== TABS ===========================
tabs = st.tabs(["👤 Demographics","💵 Salary","🚀 Promotions","🧲 Retention"])

# ========================== DEMOGRAPHICS =======================
with tabs[0]:
    # Age Distribution
    df = snapshot[['employee_id','age']].dropna()
    fig = px.histogram(df, x='age', nbins=40, color_discrete_sequence=["#0284c7"])
    card("🎂 Age Distribution", fig, df, desc="Age histogram", insights=["Dominant age bands"], recs=["Tailor benefits by age clusters"])
    # Gender Distribution
    if 'gender' in snapshot.columns:
        df2 = snapshot['gender'].value_counts().reset_index().rename(columns={'index':'gender','gender':'count'})
        fig2 = px.pie(df2, names='gender', values='count', color_discrete_sequence=px.colors.sequential.Blues)
        card("⚧ Gender Distribution", fig2, df2, desc="Employee gender ratio", insights=["Check diversity"], recs=["Promote balanced hiring"])
    # Department Count
    if 'dept_name' in snapshot.columns:
        df3 = snapshot['dept_name'].value_counts().reset_index().rename(columns={'index':'dept_name','dept_name':'count'})
        fig3 = px.bar(df3, x='dept_name', y='count', color='count', color_continuous_scale=px.colors.sequential.Blues)
        card("🏢 Employees per Department", fig3, df3, desc="Number of employees per dept", insights=["Identify largest departments"], recs=["Balance workload"])

# ========================== SALARY ===========================
with tabs[1]:
    if 'latest_salary' in snapshot.columns:
        df = snapshot[['employee_id','latest_salary','dept_name']].dropna()
        fig = px.box(df, x='dept_name', y='latest_salary', color='dept_name', color_discrete_sequence=px.colors.sequential.Greens)
        card("💰 Salary by Department", fig, df, desc="Salary distribution", insights=["Identify high/low paying depts"], recs=["Adjust pay structure"])

# ========================== PROMOTIONS =======================
with tabs[2]:
    if 'title' in snapshot.columns:
        df = snapshot.groupby('title')['employee_id'].count().reset_index().rename(columns={'employee_id':'count'})
        fig = px.bar(df, x='title', y='count', color='count', color_continuous_scale=px.colors.sequential.Purples)
        card("🚀 Employees per Title", fig, df, desc="Counts per job title", insights=["Highlights workforce concentration"], recs=["Plan talent development"])

# ========================== RETENTION =======================
with tabs[3]:
    if 'termination_date' in snapshot.columns:
        df = snapshot.dropna(subset=['termination_date'])
        df['year'] = df['termination_date'].dt.year
        df_count = df.groupby('year')['employee_id'].count().reset_index().rename(columns={'employee_id':'leavers'})
        fig = px.line(df_count, x='year', y='leavers', markers=True, color_discrete_sequence=["#f97316"])
        card("🧲 Annual Employee Turnover", fig, df_count, desc="Trend of attrition", insights=["Identify spikes"], recs=["Investigate causes"])

# ========================== SIDEBAR NAV =========================
st.sidebar.title("🗂 Quick Navigation")
sections = ["Demographics","Salary","Promotions","Retention"]
for i, sec in enumerate(sections):
    if st.sidebar.button(f"Go to {sec}"):
        tabs[i].scroll_to_view()
