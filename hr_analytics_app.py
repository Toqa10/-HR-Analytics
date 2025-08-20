import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import zipfile

# 💠 ألوان
pink = "#ff69b4"
black = "#000000"

# 🧠 تحميل البيانات من ملفات zip
@st.cache_data
def load_data():
    # مثال على salary
    with zipfile.ZipFile("data/salary.zip") as z:
        with z.open("salary.csv") as f:
            salary = pd.read_csv(f)

    # باقي الملفات CSV مباشرة
    employee = pd.read_csv("data/employee.csv")
    department = pd.read_csv("data/department.csv")
    dept_emp = pd.read_csv("data/department_employee.csv")
    dept_manager = pd.read_csv("data/department_manager.csv")
    title = pd.read_csv("data/title.csv")

    # حساب العمر
    employee['birth_date'] = pd.to_datetime(employee['birth_date'])
    employee['age'] = (datetime(2002,1,1).year - employee['birth_date'].dt.year)

    return salary, employee, department, dept_emp, dept_manager, title

# تحميل البيانات
salary, employee, department, dept_emp, dept_manager, title = load_data()

# 💼 Streamlit Dashboard
st.markdown(f"<h1 style='color:{pink}; text-align:center;'>💼 HR Analytics Dashboard</h1>", unsafe_allow_html=True)
st.markdown("---")

# اختيار التحليل
options = [
    "Top salaries",
    "Average salary per year",
    "Salary growth",
    "Distribution of Employee Ages",
    "Department with highest average salary",
    "Salary Distribution by Department"
]
question = st.selectbox("Choose a business insight:", options)
center_button = st.button("✨ Show me the Insight ✨")

if center_button and question:
    question = question.strip().lower()
    fig = None

    if question == "top salaries":
        top = salary.groupby('employee_id')['amount'].max().sort_values(ascending=False).head(10).reset_index()
        top.columns = ['Employee ID', 'Top Salary']
        st.dataframe(top.style.format({'Top Salary':'{:,.0f}'}))

    elif question == "average salary per year":
        salary['from_date'] = pd.to_datetime(salary['from_date'])
        salary['year'] = salary['from_date'].dt.year
        avg_salary = salary.groupby('year')['amount'].mean().reset_index()
        fig = px.line(avg_salary, x='year', y='amount', title="Average Salary per Year", markers=True)
    
    elif question == "salary growth":
        emp_growth = salary.groupby('employee_id')['amount'].agg(['min','max'])
        emp_growth['growth_%'] = ((emp_growth['max'] - emp_growth['min'])/emp_growth['min'])*100
        top_growth = emp_growth.sort_values('growth_%', ascending=False).head(10).reset_index()
        fig = px.bar(top_growth, x='employee_id', y='growth_%', title="Top 10 Salary Growth %", color='growth_%', color_continuous_scale='pinkyl')

    elif question == "distribution of employee ages":
        age_counts = employee['age'].value_counts().sort_index().reset_index()
        age_counts.columns = ['Age', 'Count']
        fig = px.bar(age_counts, x='Age', y='Count', title="Distribution of Employee Ages", color='Count', color_continuous_scale='pinkyl')

    elif question == "department with highest average salary":
        merged = salary.merge(employee[['id','dept_name']], left_on='employee_id', right_on='id', how='left')
        dept_avg = merged.groupby('dept_name')['amount'].mean().reset_index().sort_values('amount', ascending=False)
        fig = px.bar(dept_avg, x='dept_name', y='amount', title="Department with Highest Avg Salary", color='amount', color_continuous_scale='pinkyl')

    elif question == "salary distribution by department":
        merged = salary.merge(employee[['id','dept_name']], left_on='employee_id', right_on='id', how='left')
        fig = px.box(merged, x='dept_name', y='amount', title="Salary Distribution by Department", color='dept_name')

    if fig:
        fig.update_layout(template="plotly_dark", plot_bgcolor='black', paper_bgcolor='black', font=dict(color='pink'))
        st.plotly_chart(fig, use_container_width=True)
