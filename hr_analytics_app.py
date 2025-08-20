# hr_analytics_app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

# ===========================
# 💠 تحميل البيانات
# ===========================
@st.cache_data
def load_data():
    # ملفات محلية أو ZIP
    employee_file = "employee.csv"
    salary_file = "salary.csv"  # ممكن يكون zip: "salary.zip"
    department_file = "department.csv"
    dept_emp_file = "department_employee.csv"
    title_file = "title.csv"
    
    # قراءة الملفات
    employee = pd.read_csv(employee_file)
    salary = pd.read_csv(salary_file)
    department = pd.read_csv(department_file)
    dept_emp = pd.read_csv(dept_emp_file)
    title = pd.read_csv(title_file)
    
    # دمج بيانات الموظفين مع الأقسام
    df_merged = employee.merge(dept_emp, left_on='id', right_on='employee_id', how='left')
    df_merged = df_merged.merge(department, left_on='department_id', right_on='id', how='left')
    df_merged = df_merged.merge(salary, left_on='id', right_on='employee_id', how='left')
    
    # تحويل birth_date لـ age
    df_merged['birth_date'] = pd.to_datetime(df_merged['birth_date'], errors='coerce')
    fixed_date = pd.to_datetime('2002-01-01')
    df_merged['age'] = ((fixed_date - df_merged['birth_date']).dt.days / 365.25).astype('Int64')
    
    return employee, salary, department, dept_emp, df_merged, title

# ===========================
# تحميل البيانات
# ===========================
employee, salary, department, dept_emp, df_merged, title = load_data()

# ===========================
# Streamlit Layout
# ===========================
st.set_page_config(page_title="HR Analytics Dashboard", layout="wide")
st.title("💼 HR Analytics Dashboard")

options = [
    "Top salaries",
    "Salary growth",
    "Average tenure per department",
    "Salary vs Tenure analysis",
    "Department with highest average salary",
    "Gender pay gap",
    "Titles with highest pay",
    "Employee distribution by department",
]

question = st.selectbox("Choose a business insight:", options)
show_btn = st.button("✨ Show Insight ✨")

if show_btn and question:
    question = question.strip().lower()
    fig = None
    
    # ===========================
    # 1️⃣ Top salaries
    # ===========================
    if question == "top salaries":
        top = salary.groupby('employee_id')['amount'].max().sort_values(ascending=False).head(10).reset_index()
        top.columns = ['Employee ID', 'Top Salary']
        st.dataframe(top.style.format({'Top Salary': '{:,.0f}'}))
    
    # ===========================
    # 2️⃣ Salary growth
    # ===========================
    elif question == "salary growth":
        emp_growth = salary.groupby('employee_id')['amount'].agg(['min','max'])
        emp_growth['growth_%'] = ((emp_growth['max'] - emp_growth['min']) / emp_growth['min']) * 100
        top_growth = emp_growth.sort_values('growth_%', ascending=False).head(10).reset_index()
        fig = px.bar(top_growth, x='employee_id', y='growth_%', title="Top 10 Salary Growth %", color='growth_%', color_continuous_scale='RdPu')
    
    # ===========================
    # 3️⃣ Average tenure per department
    # ===========================
    elif question == "average tenure per department":
        dept_tenure = df_merged.groupby('dept_name')['company_tenure'].mean().reset_index()
        fig = px.bar(dept_tenure, x='dept_name', y='company_tenure', title="Average Tenure per Department", color='company_tenure', color_continuous_scale='pinkyl')
    
    # ===========================
    # 4️⃣ Salary vs Tenure
    # ===========================
    elif question == "salary vs tenure analysis":
        fig = px.scatter(df_merged, x='company_tenure', y='amount', color='dept_name', hover_data=['first_name','last_name'], title="Salary vs Tenure by Department")
    
    # ===========================
    # 5️⃣ Department with highest avg salary
    # ===========================
    elif question == "department with highest average salary":
        dept_avg = df_merged.groupby('dept_name')['amount'].mean().reset_index().sort_values('amount', ascending=False)
        fig = px.bar(dept_avg, x='dept_name', y='amount', title="Department with Highest Avg Salary", color='amount', color_continuous_scale='pinkyl')
    
    # ===========================
    # 6️⃣ Gender pay gap
    # ===========================
    elif question == "gender pay gap":
        gender_avg = df_merged.groupby('gender')['amount'].mean().reset_index()
        fig = px.bar(gender_avg, x='gender', y='amount', title="Average Salary by Gender", color='gender', color_discrete_sequence=['deeppink','purple'])
    
    # ===========================
    # 7️⃣ Titles with highest pay
    # ===========================
    elif question == "titles with highest pay":
        title_avg = df_merged.groupby('title')['amount'].mean().sort_values(ascending=False).reset_index().head(10)
        fig = px.bar(title_avg, x='title', y='amount', title="Top 10 Titles by Salary", color='amount', color_continuous_scale='pinkyl')
    
    # ===========================
    # 8️⃣ Employee distribution
    # ===========================
    elif question == "employee distribution by department":
        dist = df_merged['dept_name'].value_counts().reset_index()
        dist.columns = ['Department','Count']
        fig = px.bar(dist, x='Department', y='Count', title="Employee Distribution by Department", color='Count', color_continuous_scale='Agsunset')
    
    # ===========================
    # Show figure if exists
    # ===========================
    if fig:
        fig.update_layout(template="plotly_dark", plot_bgcolor='black', paper_bgcolor='black')
        st.plotly_chart(fig, use_container_width=True)
