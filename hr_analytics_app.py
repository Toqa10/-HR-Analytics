import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 💠 ألوان
pink = "#ff69b4"

# 🧠 تحميل البيانات من الملفات المحلية
@st.cache_data
def load_data():
    salary = pd.read_csv("salary.csv")
    employees = pd.read_csv("employee.csv")
    department = pd.read_csv("department.csv")
    dept_emp = pd.read_csv("department_employee.csv")

    # حساب العمر
    employees['birth_date'] = pd.to_datetime(employees['birth_date'])
    fixed_date = datetime(2002, 1, 1)
    employees['age'] = ((fixed_date - employees['birth_date']).dt.days / 365.25).astype(int)

    # دمج بيانات الأقسام
    df_departments = pd.merge(dept_emp, department, left_on='department_id', right_on='id', how='left')

    # دمج كل البيانات
    df_merged = pd.merge(employees, salary, left_on='id', right_on='employee_id', how='left')
    df_merged = pd.merge(df_merged, df_departments, left_on='id', right_on='employee_id', how='left')

    # استخراج السنة والشهر
    df_merged['year'] = pd.to_datetime(df_merged['hire_date']).dt.year
    df_merged['month'] = pd.to_datetime(df_merged['hire_date']).dt.month

    return employees, salary, department, dept_emp, df_merged

employees, salary, department, dept_emp, df_merged = load_data()

# 🧩 واجهة Streamlit
st.markdown(f"<h1 style='color:{pink}; text-align:center;'>💼 HR Analytics Dashboard</h1>", unsafe_allow_html=True)
st.markdown("---")

options = [
    "Top 10 Employees per Department",
    "Highest Paid Employee per Department",
    "Average Salary per Year"
]

question = st.selectbox("Choose a business insight:", options)
center_button = st.button("✨ Show me the Insight ✨")

if center_button and question:
    fig = None

    if question == "Top 10 Employees per Department":
        employee_avg_salary = df_merged.groupby(
            ['id_x', 'first_name', 'last_name', 'dept_name']
        )['amount'].mean().reset_index()

        def top_employees_per_department(df, n=10):
            return df.nlargest(n, 'amount')

        top_10 = employee_avg_salary.groupby('dept_name').apply(top_employees_per_department).reset_index(drop=True)
        st.dataframe(top_10[['first_name','last_name','dept_name','amount']])

    elif question == "Highest Paid Employee per Department":
        employee_avg_salary = df_merged.groupby(
            ['id_x', 'first_name', 'last_name', 'dept_name']
        )['amount'].mean().reset_index()

        highest_paid_per_dept = employee_avg_salary.groupby('dept_name').first().reset_index()
        highest_paid_per_dept['full_name'] = highest_paid_per_dept['first_name'] + ' ' + highest_paid_per_dept['last_name']

        fig = px.bar(
            highest_paid_per_dept,
            x='full_name',
            y='amount',
            color='dept_name',
            title='Highest Paid Employee per Department',
            labels={'full_name': 'Employee Name', 'amount': 'Salary', 'dept_name': 'Department'}
        )
        fig.update_layout(xaxis={'categoryorder':'total descending'})

    elif question == "Average Salary per Year":
        avg_salary_per_year = df_merged.groupby('year')['amount'].mean().reset_index()
        fig = px.line(avg_salary_per_year, x='year', y='amount', title='Average Salary Over Time')
        fig.update_traces(mode='lines+markers')

    if fig:
        fig.update_layout(template='plotly_dark', plot_bgcolor='black', paper_bgcolor='black', font=dict(color=pink))
        st.plotly_chart(fig, use_container_width=True)

