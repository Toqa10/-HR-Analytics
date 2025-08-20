# hr_analytics_app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score

# ----------------------------
# تحميل البيانات المحلية
# ----------------------------
@st.cache_data
def load_data():
    salary = pd.read_csv("salary.csv")
    employee = pd.read_csv("employee.csv")
    dept_emp = pd.read_csv("department_employee.csv")
    department = pd.read_csv("department.csv")
    title = pd.read_csv("title.csv")
    
    # حساب العمر
    employee['birth_date'] = pd.to_datetime(employee['birth_date'])
    employee['age'] = datetime.now().year - employee['birth_date'].dt.year
    
    # دمج البيانات
    df_merged = employee.merge(salary, left_on='id', right_on='employee_id', how='left')
    df_merged = df_merged.merge(dept_emp, left_on='id', right_on='employee_id', how='left')
    df_merged = df_merged.merge(department, left_on='department_id', right_on='id', how='left')
    
    return employee, salary, department, dept_emp, df_merged, title

employee, salary, department, dept_emp, df_merged, title = load_data()

# ----------------------------
# Streamlit UI
# ----------------------------
st.title("💼 HR Analytics Dashboard")
st.markdown("---")

# خيارات التحليل
options = [
    "Top Salaries",
    "Salary Growth Over Time",
    "Average Tenure per Department",
    "Salary vs Tenure Analysis",
    "Department with Highest Avg Salary",
    "Gender Pay Gap",
    "Titles with Highest Pay",
    "Moved Departments Tracking",
    "Turnover Analysis",
]

question = st.selectbox("Choose a business insight:", options)
center_button = st.button("✨ Show Insight ✨")

if center_button:
    if question == "Top Salaries":
        top = salary.groupby('employee_id')['amount'].max().sort_values(ascending=False).head(10).reset_index()
        top = top.merge(employee[['id','first_name','last_name']], left_on='employee_id', right_on='id')
        top['full_name'] = top['first_name'] + ' ' + top['last_name']
        fig = px.bar(top, x='full_name', y='amount', title="💰 Top 10 Salaries")
        st.plotly_chart(fig)

    elif question == "Salary Growth Over Time":
        salary['from_date'] = pd.to_datetime(salary['from_date'])
        salary['year'] = salary['from_date'].dt.year
        avg_salary = salary.groupby('year')['amount'].mean().reset_index()
        fig = px.line(avg_salary, x='year', y='amount', title="📈 Average Salary Growth Over Time")
        st.plotly_chart(fig)

    elif question == "Department with Highest Avg Salary":
        merged = df_merged.groupby('dept_name')['amount'].mean().reset_index().sort_values(by='amount', ascending=False)
        fig = px.bar(merged, x='dept_name', y='amount', title="🏢 Department with Highest Avg Salary")
        st.plotly_chart(fig)

    elif question == "Salary vs Tenure Analysis":
        if 'company_tenure' not in df_merged.columns:
            df_merged['company_tenure'] = (pd.to_datetime('2025-01-01') - pd.to_datetime(df_merged['hire_date'])).dt.days/365
        fig = px.scatter(df_merged, x='company_tenure', y='amount', color='dept_name',
                         hover_data=['first_name','last_name'], title="⏳ Salary vs Tenure by Department")
        st.plotly_chart(fig)
    
    else:
        st.warning("⚠️ This insight is not yet implemented.")

# ----------------------------
# Bonus Prediction
# ----------------------------
st.markdown("---")
st.header("🤖 Bonus Prediction")

with st.form("bonus_form"):
    salary_input = st.number_input("Current Salary", min_value=0)
    tenure_input = st.number_input("Tenure (Years)", min_value=0)
    dept_input = st.selectbox("Department", df_merged['dept_name'].unique())
    title_input = st.selectbox("Title", df_merged['title'].dropna().unique())
    gender_input = st.selectbox("Gender", ['M','F'])
    submit_button = st.form_submit_button("Predict Bonus")

if submit_button:
    # إعداد البيانات للتنبؤ
    df_model = df_merged[['amount','company_tenure','dept_name','title','gender']].dropna()
    df_model['bonus'] = ((df_model['amount'].shift(-1) - df_model['amount'])/df_model['amount']) > 0.05
    df_model.dropna(inplace=True)
    
    # ترميز الفئات
    le_dept = LabelEncoder()
    le_title = LabelEncoder()
    le_gender = LabelEncoder()
    df_model['dept_enc'] = le_dept.fit_transform(df_model['dept_name'])
    df_model['title_enc'] = le_title.fit_transform(df_model['title'])
    df_model['gender_enc'] = le_gender.fit_transform(df_model['gender'])
    
    X = df_model[['amount','company_tenure','dept_enc','title_enc','gender_enc']]
    y = df_model['bonus']
    
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X, y)
    
    # تحويل إدخال المستخدم
    input_df = pd.DataFrame({
        'amount':[salary_input],
        'company_tenure':[tenure_input],
        'dept_enc':[le_dept.transform([dept_input])[0]],
        'title_enc':[le_title.transform([title_input])[0]],
        'gender_enc':[le_gender.transform([gender_input])[0]]
    })
    
    pred = clf.predict(input_df)[0]
    if pred:
        st.success("🎉 This employee is likely to get a bonus!")
    else:
        st.info("❌ This employee is unlikely to get a bonus.")
