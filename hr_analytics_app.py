# app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

st.set_page_config(page_title="HR Analytics Dashboard", layout="wide")

st.title("🔍 HR Analytics Dashboard & Bonus Predictor")

# =========================
# Step 1: Upload CSV files
# =========================
salary_file = st.file_uploader("Upload salary.csv", type="csv")
employee_file = st.file_uploader("Upload employee.csv", type="csv")
department_file = st.file_uploader("Upload department.csv", type="csv")
dept_emp_file = st.file_uploader("Upload department_employee.csv", type="csv")

if salary_file and employee_file and department_file and dept_emp_file:
    salary = pd.read_csv(salary_file)
    employee = pd.read_csv(employee_file)
    department = pd.read_csv(department_file)
    dept_emp = pd.read_csv(dept_emp_file)

    st.success("✅ All files loaded successfully!")

    # =========================
    # Step 2: Prepare data
    # =========================
    employee['birth_date'] = pd.to_datetime(employee['birth_date'])
    employee['age'] = (pd.to_datetime('2002-01-01') - employee['birth_date']).dt.days // 365

    df_merged = employee.merge(salary, left_on='id', right_on='employee_id', how='left')
    df_departments = dept_emp.merge(department, left_on='department_id', right_on='id', how='left')
    df_merged = df_merged.merge(df_departments, left_on='id', right_on='employee_id', how='left')

    # =========================
    # Step 3: Business Questions
    # =========================
    st.header("📊 Business Questions Dashboard")
    option = st.selectbox("Choose an insight:", [
        "Top salaries",
        "Salary growth",
        "Department with highest average salary",
        "Salary vs Tenure",
        "Gender pay gap",
        "Titles with highest pay"
    ])

    if option == "Top salaries":
        top = salary.groupby('employee_id')['amount'].max().sort_values(ascending=False).head(10)
        st.dataframe(top)

    elif option == "Salary growth":
        emp_growth = salary.groupby('employee_id')['amount'].agg(['min','max'])
        emp_growth['growth_%'] = ((emp_growth['max'] - emp_growth['min']) / emp_growth['min'])*100
        st.bar_chart(emp_growth['growth_%'])

    elif option == "Department with highest average salary":
        merged = df_merged.groupby('dept_name')['amount'].mean().sort_values(ascending=False)
        st.bar_chart(merged)

    elif option == "Salary vs Tenure":
        if 'company_tenure' in df_merged.columns:
            fig = px.scatter(df_merged, x='company_tenure', y='amount', color='dept_name',
                             title='Salary vs Tenure by Department', hover_data=['first_name','last_name'])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Column 'company_tenure' not found!")

    elif option == "Gender pay gap":
        if 'gender' in df_merged.columns:
            gender_avg = df_merged.groupby('gender')['amount'].mean()
            st.bar_chart(gender_avg)
        else:
            st.warning("Column 'gender' not found!")

    elif option == "Titles with highest pay":
        title_avg = df_merged.groupby('title')['amount'].mean().sort_values(ascending=False).head(10)
        st.bar_chart(title_avg)

    # =========================
    # Step 4: Bonus Prediction
    # =========================
    st.header("🤖 Bonus Prediction")
    df_bonus = df_merged.copy()
    df_bonus['bonus'] = ((df_bonus['amount'] - df_bonus['amount'].shift(1)) / df_bonus['amount'].shift(1)) > 0.05
    df_bonus['bonus'] = df_bonus['bonus'].astype(int)
    df_bonus.dropna(inplace=True)

    # Encode categorical
    le_dept = LabelEncoder()
    df_bonus['dept_name_enc'] = le_dept.fit_transform(df_bonus['dept_name'].astype(str))
    le_title = LabelEncoder()
    df_bonus['title_enc'] = le_title.fit_transform(df_bonus['title'].astype(str))

    X = df_bonus[['amount','dept_name_enc','title_enc','age']]
    y = df_bonus['bonus']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestClassifier()
    model.fit(X_train, y_train)

    st.subheader("Enter Employee Info for Prediction:")
    salary_input = st.number_input("Current Salary")
    dept_input = st.selectbox("Department", df_bonus['dept_name'].unique())
    title_input = st.selectbox("Title", df_bonus['title'].unique())
    age_input = st.number_input("Age", min_value=18, max_value=100, value=30)

    if st.button("Predict Bonus"):
        input_df = pd.DataFrame({
            'amount':[salary_input],
            'dept_name_enc':[le_dept.transform([dept_input])[0]],
            'title_enc':[le_title.transform([title_input])[0]],
            'age':[age_input]
        })
        prediction = model.predict(input_df)[0]
        if prediction == 1:
            st.success("🎉 Employee likely to get a bonus!")
        else:
            st.warning("😕 Employee unlikely to get a bonus.")

