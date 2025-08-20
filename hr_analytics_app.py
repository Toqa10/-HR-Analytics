import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

# 💠 ألوان
pink = "#ff69b4"
black = "#000000"

# 🧠 تحميل البيانات مع التحقق من وجود الملفات
@st.cache_data
def load_data():
    file_list = ["salary.csv", "employee.csv", "department.csv", "department_employee.csv"]
    missing_files = [f for f in file_list if not os.path.exists(f)]
    if missing_files:
        raise FileNotFoundError(f"الملفات التالية غير موجودة: {', '.join(missing_files)}")

    salary = pd.read_csv("salary.csv")
    employee = pd.read_csv("employee.csv")
    department = pd.read_csv("department.csv")
    dept_emp = pd.read_csv("department_employee.csv")

    # حساب العمر
    employee["birth_date"] = pd.to_datetime(employee["birth_date"])
    fixed_date = datetime(2002, 1, 1)
    employee["age"] = ((fixed_date - employee["birth_date"]).dt.days / 365.25).astype(int)

    # دمج البيانات
    df_departments = pd.merge(dept_emp, department, left_on='department_id', right_on='id', how='left')
    df_merged = pd.merge(employee, salary, left_on='id', right_on='employee_id', how='left')
    df_merged = pd.merge(df_merged, df_departments, left_on='id', right_on='employee_id', how='left')

    # استخراج السنة والشهر
    df_merged['year'] = pd.to_datetime(df_merged['hire_date']).dt.year
    df_merged['month'] = pd.to_datetime(df_merged['hire_date']).dt.month

    return employee, salary, department, dept_emp, df_merged

# 🗂️ تحميل البيانات
try:
    employees, salary, department, dept_emp, df_merged = load_data()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

# تخصيص CSS للتصميم (نجوم + pink theme)
st.markdown("""
<style>
/* الخلفية */
[data-testid="stAppViewContainer"] { background-color: black; }
/* النجوم */
.star { position: fixed; border-radius: 50%; animation: blink 2s infinite ease-in-out; opacity: 0.8; pointer-events: none; }
@keyframes blink {0%,100%{opacity:0.2;}50%{opacity:1;}}
.star1 { top:10%; left:20%; width:2px; height:2px; background-color:#ff69b4; animation-delay:0s;}
.star2 { top:20%; left:70%; width:3px; height:3px; background-color:#ba55d3; animation-delay:0.4s;}
.star3 { top:30%; left:40%; width:1.5px; height:1.5px; background-color:#dda0dd; animation-delay:1s;}
.star4 { top:50%; left:60%; width:2.5px; height:2.5px; background-color:#ff1493; animation-delay:0.2s;}
.star5 { top:70%; left:25%; width:1.8px; height:1.8px; background-color:#db7093; animation-delay:1.4s;}
.star6 { top:80%; left:85%; width:1.3px; height:1.3px; background-color:#d8bfd8; animation-delay:0.8s;}
.star7 { top:15%; left:90%; width:2.2px; height:2.2px; background-color:#c71585; animation-delay:0.6s;}
.star8 { top:65%; left:10%; width:2.1px; height:2.1px; background-color:#ffb6c1; animation-delay:1.2s;}
/* نصوص */
h1, .stSelectbox label, .stButton button { color:#ffffff; font-family: 'Segoe UI', sans-serif; font-size:28px; }
.stSelectbox>div>div { font-size:22px; }
.stButton button { border:2px solid #ff69b4; background-color:#222; color:#fff; border-radius:30px; font-size:24px; padding:20px 50px; transition:all 0.3s ease-in-out; }
.stButton button:hover { background-color:#ff69b4; color:#000; transform:scale(1.08); box-shadow:0 0 15px #ff69b4; }
</style>
<div class="star star1"></div>
<div class="star star2"></div>
<div class="star star3"></div>
<div class="star star4"></div>
<div class="star star5"></div>
<div class="star star6"></div>
<div class="star star7"></div>
<div class="star star8"></div>
""", unsafe_allow_html=True)

st.markdown(f"<h1 style='color:{pink}; text-align:center;'>💼 HR Analytics Dashboard</h1>", unsafe_allow_html=True)
st.markdown("---")

# 🧩 خيارات التحليلات
options = [
    "Top Salaries",
    "Average Salary per Year",
    "Salary Growth",
    "Distribution of Employee Ages",
    "Department with Highest Average Salary",
    "Highest Paid Employee per Department"
]

question = st.selectbox("Choose a business insight:", options)
show_btn = st.button("✨ Show Insight ✨")

# 🖥️ عرض النتائج
if show_btn and question:
    fig = None

    if question.lower() == "top salaries":
        top = salary.groupby('employee_id')['amount'].max().sort_values(ascending=False).head(10).reset_index()
        top.columns = ['Employee ID', 'Top Salary']
        st.markdown("### 💰 Top 10 Salaries (Table View)")
        st.dataframe(top.style.format({'Top Salary':'{:,.0f}'}).background_gradient(cmap='pink'), use_container_width=True)

    elif question.lower() == "average salary per year":
        salary['from_date'] = pd.to_datetime(salary['from_date'])
        salary['year'] = salary['from_date'].dt.year
        avg_salary = salary.groupby('year')['amount'].mean().reset_index()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=avg_salary['year'], y=avg_salary['amount'], mode='lines+markers', line=dict(color='deeppink', width=3)))
        fig.update_layout(title='Average Salary Over Time', xaxis_title='Year', yaxis_title='Average Salary', template='plotly_dark', plot_bgcolor='black', paper_bgcolor='black', font=dict(color='pink'))

    elif question.lower() == "salary growth":
        emp_growth = salary.groupby('employee_id')['amount'].agg(['min','max'])
        emp_growth['growth_%'] = ((emp_growth['max']-emp_growth['min'])/emp_growth['min'])*100
        top_growth = emp_growth.sort_values('growth_%', ascending=False).head(10).reset_index()
        fig = px.bar(top_growth, x='employee_id', y='growth_%', title="Top 10 Salary Growth %", color='growth_%', color_continuous_scale='RdPu')

    elif question.lower() == "distribution of employee ages":
        age_counts = employees['age'].value_counts().sort_index().reset_index()
        age_counts.columns = ['Age','Count']
        fig = px.bar(age_counts, x='Count', y='Age', orientation='h', title='🎂 Distribution of Employee Ages', color='Count', color_continuous_scale='Pinkyl', text='Count')
        fig.update_traces(textposition='outside')

    elif question.lower() == "department with highest average salary":
        merged = pd.merge(df_merged[['id','dept_name']], salary, left_on='id', right_on='employee_id')
        dept_avg = merged.groupby('dept_name')['amount'].mean().reset_index().sort_values('amount', ascending=False)
        fig = px.bar(dept_avg, x='dept_name', y='amount', title="Avg Salary per Department", color='amount', color_continuous_scale='Pinkyl')

    elif question.lower() == "highest paid employee per department":
        employee_avg_salary = df_merged.groupby(['id_x','first_name','last_name','dept_name'])['amount'].mean().reset_index()
        top_10_employees_per_dept = employee_avg_salary.groupby('dept_name').apply(lambda x: x.nlargest(1,'amount')).reset_index(drop=True)
        top_10_employees_per_dept['full_name'] = top_10_employees_per_dept['first_name'] + ' ' + top_10_employees_per_dept['last_name']
        fig = px.bar(top_10_employees_per_dept, x='full_name', y='amount', color='dept_name', title='Highest Paid Employee per Department')
        fig.update_layout(xaxis={'categoryorder':'total descending'})

    # عرض الرسم إذا موجود
    if fig:
        st.plotly_chart(fig, use_container_width=True)

st.markdown(f"<p style='color:{pink}; font-size:12px; text-align:center;'>Made with ❤️ by Mayar</p>", unsafe_allow_html=True)
