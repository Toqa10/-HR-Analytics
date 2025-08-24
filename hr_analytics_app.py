import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# ========================== PAGE SETUP ==========================
st.set_page_config(page_title="HR Analytics Dashboard", layout="wide")

# ========================== LOAD DATA ==========================
@st.cache_data
def load_data():
    employee = pd.read_csv("employee.csv")
    salary = pd.read_csv("salary.csv") if "salary.csv" in st.session_state else pd.DataFrame()
    title = pd.read_csv("title.csv") if "title.csv" in st.session_state else pd.DataFrame()
    return employee, salary, title

employee, salary, title = load_data()

# ========================== DATA PREP ==========================
if 'id' in employee.columns:
    employee = employee.rename(columns={'id': 'employee_id'})

def to_dt(df, col):
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    return df

for col in ['birth_date','hire_date','termination_date']:
    employee = to_dt(employee, col)

# Compute additional columns
employee['age'] = datetime.now().year - employee['birth_date'].dt.year
employee['company_tenure'] = (pd.Timestamp.today() - employee['hire_date']).dt.days/365.25

# ========================== SIDEBAR FILTER ==========================
st.sidebar.header("Filters for Dashboard")

# Demographics filters
demographics_sharts = {
    "Age Distribution": True,
    "Age by Department": True,
    "Headcount by Department": True,
    "Gender Mix": True,
}

st.sidebar.subheader("Demographics Charts")
for chart in demographics_sharts:
    demographics_sharts[chart] = st.sidebar.checkbox(chart, value=True)

# Salaries filters
salaries_charts = {
    "Average Salary Over Time": True,
    "Top 20 Salaries": True,
    "Salary Distribution": True,
    "Average Salary by Department": True,
}

st.sidebar.subheader("Salaries Charts")
for chart in salaries_charts:
    salaries_charts[chart] = st.sidebar.checkbox(chart, value=True)

# Promotions filters
promotions_charts = {
    "Promotions per Year": True,
    "Time to First Promotion": True,
    "Promotions by Department": True,
}

st.sidebar.subheader("Promotions Charts")
for chart in promotions_charts:
    promotions_charts[chart] = st.sidebar.checkbox(chart, value=True)

# Retention filters
retention_charts = {
    "Tenure Distribution": True,
    "Attrition by Tenure Band": True,
    "1-Year Retention by Hire Cohort": True,
}

st.sidebar.subheader("Retention Charts")
for chart in retention_charts:
    retention_charts[chart] = st.sidebar.checkbox(chart, value=True)

# ========================== TABS ==========================
tab1, tab2, tab3, tab4 = st.tabs(["Demographics", "Salaries", "Promotions", "Retention"])

# ========================== DEMOGRAPHICS ==========================
with tab1:
    if demographics_sharts["Age Distribution"]:
        fig = px.histogram(employee.dropna(subset=['age']), x='age', nbins=40, title="Age Distribution")
        st.plotly_chart(fig, use_container_width=True)

    if demographics_sharts["Age by Department"] and 'dept_name' in employee.columns:
        tmp = employee.dropna(subset=['age','dept_name'])
        tmp['age_group'] = pd.cut(tmp['age'], [10,20,30,40,50,60,70], labels=['10s','20s','30s','40s','50s','60s'], right=False)
        pivot = tmp.pivot_table(index='dept_name', columns='age_group', values='employee_id', aggfunc='count', fill_value=0).reset_index()
        fig = px.bar(pivot, x='dept_name', y=pivot.columns[1:], barmode='stack', title="Age Group by Department")
        st.plotly_chart(fig, use_container_width=True)

    if demographics_sharts["Headcount by Department"] and 'dept_name' in employee.columns:
        dep = employee['dept_name'].value_counts().reset_index()
        dep.columns = ['Department','Headcount']
        fig = px.bar(dep, x='Department', y='Headcount', title="Headcount by Department")
        st.plotly_chart(fig, use_container_width=True)

    if demographics_sharts["Gender Mix"] and 'gender' in employee.columns:
        gen = employee['gender'].value_counts().reset_index()
        gen.columns = ['gender','count']
        fig = px.pie(gen, names='gender', values='count', title="Gender Mix")
        st.plotly_chart(fig, use_container_width=True)

# ========================== SALARIES ==========================
with tab2:
    if salaries_charts["Average Salary Over Time"] and not salary.empty:
        s = salary.copy(); s['from_date'] = pd.to_datetime(s['from_date'], errors='coerce'); s['year'] = s['from_date'].dt.year
        avg = s.groupby('year')['amount'].mean().reset_index()
        fig = px.line(avg, x='year', y='amount', markers=True, title="Average Salary Over Time")
        st.plotly_chart(fig, use_container_width=True)

    if salaries_charts["Top 20 Salaries"] and not salary.empty:
        top = salary.groupby('employee_id')['amount'].max().sort_values(ascending=False).head(20).reset_index()
        fig = px.bar(top, x='employee_id', y='amount', title="Top 20 Salaries")
        st.plotly_chart(fig, use_container_width=True)

    if salaries_charts["Salary Distribution"] and not salary.empty:
        fig = px.histogram(salary, x='amount', nbins=40, title="Salary Distribution")
        st.plotly_chart(fig, use_container_width=True)

    if salaries_charts["Average Salary by Department"] and not salary.empty and 'dept_name' in employee.columns:
        m = employee[['employee_id','dept_name']].merge(salary[['employee_id','amount']], on='employee_id', how='left').dropna()
        g = m.groupby('dept_name')['amount'].mean().reset_index().sort_values('amount', ascending=False)
        fig = px.bar(g, x='dept_name', y='amount', title="Average Salary by Department")
        st.plotly_chart(fig, use_container_width=True)

# ========================== PROMOTIONS ==========================
with tab3:
    if promotions_charts["Promotions per Year"] and not title.empty:
        tdf = title.copy(); tdf['from_date'] = pd.to_datetime(tdf['from_date'], errors='coerce')
        tdf = tdf.sort_values(['employee_id','from_date'])
        tdf['prev_title'] = tdf.groupby('employee_id')['title'].shift()
        tdf['changed'] = (tdf['title'] != tdf['prev_title']).astype(int)
        tdf['year'] = tdf['from_date'].dt.year
        per_year = tdf[tdf['changed']==1].groupby('year').size().reset_index(name='Promotions')
        fig = px.bar(per_year, x='year', y='Promotions', title="Promotions per Year")
        st.plotly_chart(fig, use_container_width=True)

    if promotions_charts["Time to First Promotion"] and not title.empty:
        first_change = tdf[tdf['changed']==1].groupby('employee_id')['from_date'].min().reset_index().rename(columns={'from_date':'first_promo_date'})
        tmp = employee[['employee_id','hire_date']].merge(first_change, on='employee_id', how='inner')
        tmp['time_to_first_promo_years'] = (tmp['first_promo_date'] - tmp['hire_date']).dt.days/365.25
        fig = px.histogram(tmp, x='time_to_first_promo_years', nbins=30, title="Time to First Promotion (Years)")
        st.plotly_chart(fig, use_container_width=True)

    if promotions_charts["Promotions by Department"] and not title.empty and 'dept_name' in employee.columns:
        promos = tdf.groupby('employee_id')['changed'].sum().reset_index(name='promotion_count')
        pmap = promos.merge(employee[['employee_id','dept_name']], on='employee_id', how='left')
        by_dept = pmap.groupby('dept_name')['promotion_count'].sum().reset_index().sort_values('promotion_count', ascending=False)
        fig = px.bar(by_dept, x='dept_name', y='promotion_count', title="Promotions by Department")
        st.plotly_chart(fig, use_container_width=True)

# ========================== RETENTION ==========================
with tab4:
    if retention_charts["Tenure Distribution"]:
        fig = px.histogram(employee.dropna(subset=['company_tenure']), x='company_tenure', nbins=40, title="Tenure Distribution")
        st.plotly_chart(fig, use_container_width=True)

    if retention_charts["Attrition by Tenure Band"] and 'termination_date' in employee.columns:
        e = employee.dropna(subset=['termination_date'])
        e['tenure_at_exit'] = (e['termination_date'] - e['hire_date']).dt.days/365.25
        e['band'] = pd.cut(e['tenure_at_exit'], [0,1,2,3,5,10,50], labels=['<1y','1-2y','2-3y','3-5y','5-10y','10y+'], right=False)
        fig = px.histogram(e, x='band', title="Attrition by Tenure Band")
        st.plotly_chart(fig, use_container_width=True)

    if retention_charts["1-Year Retention by Hire Cohort"]:
        e = employee.copy()
        e['cohort'] = e['hire_date'].dt.year
        e['left'] = ~e['termination_date'].isna()
        e['retained_1y'] = (~e['left']) | ((e['termination_date'] - e['hire_date']).dt.days >= 365)
        g = e.groupby('cohort')['retained_1y'].mean().reset_index()
        g['Retention%_1y'] = g['retained_1y']*100
        fig = px.bar(g, x='cohort', y='Retention%_1y', title="1-Year Retention by Hire Cohort")
        st.plotly_chart(fig, use_container_width=True)
