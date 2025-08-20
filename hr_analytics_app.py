import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import patoolib  # للتعامل مع ملفات RAR
import os

# 💠 ألوان
pink = "#ff69b4"
black = "#000000"

# 🧠 تحميل البيانات من RAR أو CSV
@st.cache_data
def load_data():
    # فك ضغط ملف salary.rar لو موجود
    if not os.path.exists("salary.csv"):
        patoolib.extract_archive("salary.rar", outdir=".")
    
    salary = pd.read_csv("salary.csv")
    employee = pd.read_csv("employee.csv", encoding='utf-8')
    current_emp_snapshot = pd.read_csv("current_employee_snapshot.csv", encoding='utf-8')
    department = pd.read_csv("department.csv", encoding='utf-8') 
    department_employee = pd.read_csv("department_employee.csv", encoding='utf-8')
    department_manager = pd.read_csv("department_manager.csv", encoding='utf-8')
    title = pd.read_csv("title.csv", encoding='utf-8')

    # حساب العمر
    emp_snapshot = current_emp_snapshot.merge(employee, left_on="employee_id", right_on="id", how="left")
    emp_snapshot["birth_date"] = pd.to_datetime(emp_snapshot["birth_date"])
    emp_snapshot["age"] = datetime(2002, 12, 12).year - emp_snapshot["birth_date"].dt.year
    emp_snapshot.dropna(subset=["salary_amount"], inplace=True)

    return salary, employee, emp_snapshot, department_employee, department, department_manager, title

# 🗂️ تحميل كل البيانات
salary, employee, current_emp_snapshot, department_employee, department, department_manager, title = load_data()

# 🧩 تأمين الأعمدة المفقودة (مؤقتًا)
for col in ['age', 'title', 'dept_name', 'company_tenure', 'moved_department']:
    if col not in employee.columns:
        employee[col] = np.nan

emp_snapshot = current_emp_snapshot.copy()

# Streamlit Title
st.markdown(f"<h1 style='color:{pink}; text-align:center;'>💼 HR Analytics Dashboard</h1>", unsafe_allow_html=True)
st.markdown("---")

# قائمة الأسئلة
options = [
    "top salaries",
    "average salary per year",
    "salary growth",
    "Distribution of Employee Ages",
    "department with highest average salary",
    "Distribution of Tenure Years per Department",
    "Tenure vs Salary by Department",
    "Salary Distribution by Department",
    "employee distribution",
    "Average Salary per Job Title",
    "common titles by age group"
]

question = st.selectbox("Choose a business insight:", options)
center_button = st.button("✨ Show me the Insight ✨")

if center_button and question:
    question = question.strip().lower()
    fig = None

    if question == "top salaries":
        top = salary.groupby('employee_id')['amount'].max().sort_values(ascending=False).head(10).reset_index()
        top.columns = ['Employee ID', 'Top Salary']
        st.markdown("### 💰 Top 10 Salaries (Table View)")
        st.dataframe(top.style.format({'Top Salary': '{:,.0f}'}), use_container_width=True)

    elif question == "average salary per year":
        salary['from_date'] = pd.to_datetime(salary['from_date'])
        salary['year'] = salary['from_date'].dt.year
        avg_salary_per_year = salary.groupby('year')['amount'].mean().reset_index()
        fig = px.line(avg_salary_per_year, x='year', y='amount', title='Average Salary Over Time', markers=True)
    
    elif question == "salary growth":
        emp_growth = salary.groupby('employee_id')['amount'].agg(['min', 'max'])
        emp_growth['growth_%'] = ((emp_growth['max'] - emp_growth['min']) / emp_growth['min']) * 100
        top_growth = emp_growth.sort_values(by='growth_%', ascending=False).head(10).reset_index()
        fig = px.bar(top_growth, x='employee_id', y='growth_%', title="Top 10 Salary Growth %", color='growth_%', color_continuous_scale='RdPu')

    elif question == "distribution of employee ages":
        age_counts = current_emp_snapshot['age'].value_counts().sort_index().reset_index()
        age_counts.columns = ['Age', 'Count']
        fig = px.bar(age_counts, x='Age', y='Count', title='🎂 Distribution of Employee Ages', color='Count', color_continuous_scale='pinkyl')

    elif question == "department with highest average salary":
        merged = current_emp_snapshot[['employee_id', 'dept_name']].merge(salary, on='employee_id')
        dept_avg = merged.groupby('dept_name')['amount'].mean().reset_index().sort_values(by='amount', ascending=False)
        fig = px.bar(dept_avg, x='dept_name', y='amount', title="Avg Salary per Department", color='amount', color_continuous_scale='pinkyl')

    # ... هنا يمكنك إضافة باقي الأسئلة بنفس الطريقة

    # عرض الشارت
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)

st.markdown(f"<p style='color:{pink}; font-size:12px; text-align:center;'>Made with ❤️ by Mayar</p>", unsafe_allow_html=True)
