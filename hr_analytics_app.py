import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score
import patoolib
import os

# 💠 ألوان
pink = "#ff69b4"
black = "#000000"

# 🧠 تحميل البيانات
@st.cache_data
def load_data():
    # فك ضغط ملف salary.rar
    if not os.path.exists("salary.csv") and os.path.exists("salary.rar"):
        patoolib.extract_archive("salary.rar", outdir=".")
    
    salary = pd.read_csv("salary.csv")
    employee = pd.read_csv("employee.csv")
    current_emp_snapshot = pd.read_csv("current_employee_snapshot.csv")
    department = pd.read_csv("department.csv")
    department_employee = pd.read_csv("department_employee.csv")
    department_manager = pd.read_csv("department_manager.csv")
    title = pd.read_csv("title.csv")

    # حساب العمر
    emp_snapshot = current_emp_snapshot.merge(employee, left_on="employee_id", right_on="id", how="left")
    emp_snapshot["birth_date"] = pd.to_datetime(emp_snapshot["birth_date"])
    emp_snapshot["age"] = datetime(2002, 12, 12).year - emp_snapshot["birth_date"].dt.year
    emp_snapshot.dropna(subset=["salary_amount"], inplace=True)

    return salary, employee, emp_snapshot, department_employee, department, department_manager, title

# تحميل البيانات
salary, employee, emp_snapshot, dept_emp, department, dept_manager, title = load_data()

# 🧩 تأمين الأعمدة المفقودة
for col in ['age', 'title', 'dept_name', 'company_tenure', 'moved_department']:
    if col not in employee.columns:
        employee[col] = np.nan

# Streamlit Title
st.markdown(f"<h1 style='color:{pink}; text-align:center;'>💼 HR Analytics Dashboard + Bonus Prediction</h1>", unsafe_allow_html=True)
st.markdown("---")

# ------------------ قسم Business Questions ------------------
st.subheader("🔍 Business Questions")
options = [
    "Top Salaries",
    "Salary Growth",
    "Average Tenure per Department",
    "Salary vs Tenure Analysis",
    "Department with Highest Average Salary",
    "Gender Pay Gap",
    "Titles with Highest Pay",
    "Moved Departments Tracking",
    "Turnover Analysis"
]
question = st.selectbox("Choose a business insight:", options)
show_btn = st.button("✨ Show Insight ✨")

if show_btn:
    fig = None
    if question == "Top Salaries":
        top = salary.groupby('employee_id')['amount'].max().sort_values(ascending=False).head(10).reset_index()
        top.columns = ['Employee ID', 'Top Salary']
        st.dataframe(top.style.format({'Top Salary':'{:,.0f}'}))
    elif question == "Salary Growth":
        emp_growth = salary.groupby('employee_id')['amount'].agg(['min','max'])
        emp_growth['growth_%'] = ((emp_growth['max']-emp_growth['min'])/emp_growth['min'])*100
        top_growth = emp_growth.sort_values(by='growth_%', ascending=False).head(10).reset_index()
        fig = px.bar(top_growth, x='employee_id', y='growth_%', color='growth_%', title="Top 10 Salary Growth %", color_continuous_scale='RdPu')
    elif question == "Average Tenure per Department":
        dept_tenure = emp_snapshot.groupby('dept_name')['company_tenure'].mean().reset_index()
        fig = px.bar(dept_tenure, x='dept_name', y='company_tenure', title='Average Tenure per Department', color='company_tenure', color_continuous_scale='pinkyl')
    elif question == "Salary vs Tenure Analysis":
        merged = emp_snapshot.merge(salary, on='employee_id')
        fig = px.scatter(merged, x='company_tenure', y='amount', color='dept_name', title="Salary vs Tenure by Department", hover_data=['employee_id'])
    elif question == "Department with Highest Average Salary":
        merged = emp_snapshot[['employee_id','dept_name']].merge(salary, on='employee_id')
        dept_avg = merged.groupby('dept_name')['amount'].mean().reset_index().sort_values(by='amount', ascending=False)
        fig = px.bar(dept_avg, x='dept_name', y='amount', color='amount', title="Department with Highest Average Salary", color_continuous_scale='pinkyl')
    elif question == "Gender Pay Gap":
        merged = emp_snapshot[['employee_id','gender']].merge(salary, on='employee_id')
        gender_avg = merged.groupby('gender')['amount'].mean().reset_index()
        fig = px.bar(gender_avg, x='gender', y='amount', color='gender', title="Gender Pay Gap", color_discrete_sequence=['deeppink','mediumvioletred'])
    elif question == "Titles with Highest Pay":
        merged = emp_snapshot[['employee_id','title']].merge(salary, on='employee_id')
        title_avg = merged.groupby('title')['amount'].mean().sort_values(ascending=False).reset_index()
        fig = px.bar(title_avg.head(10), x='title', y='amount', color='amount', title="Top Titles by Average Salary", color_continuous_scale='pinkyl')
    elif question == "Moved Departments Tracking":
        moved = emp_snapshot[emp_snapshot['moved_department']==1]
        fig = px.bar(moved['dept_name'].value_counts().reset_index(), x='index', y='dept_name', title="Moved Departments Count", color='dept_name', color_continuous_scale='pinkyl')
    elif question == "Turnover Analysis":
        turnover = emp_snapshot[emp_snapshot['left_company']==1] if 'left_company' in emp_snapshot.columns else pd.DataFrame()
        if not turnover.empty:
            fig = px.bar(turnover['dept_name'].value_counts().reset_index(), x='index', y='dept_name', title="Turnover per Department", color='dept_name', color_continuous_scale='pinkyl')
        else:
            st.info("No turnover data available.")

    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)

# ------------------ قسم Bonus Prediction ------------------
st.subheader("🤖 Bonus Prediction")
st.markdown("Predict if an employee will get a bonus (>5% salary increase)")

# Prepare data for modeling
data_model = emp_snapshot.merge(salary, on='employee_id')
data_model['bonus'] = ((data_model['amount'] - data_model['salary_amount'])/data_model['salary_amount'] > 0.05).astype(int)
features = ['amount','company_tenure','age']
for cat_col in ['dept_name','title','gender']:
    if cat_col in data_model.columns:
        le = LabelEncoder()
        data_model[cat_col] = le.fit_transform(data_model[cat_col].astype(str))
        features.append(cat_col)

X = data_model[features]
y = data_model['bonus']

# Train RandomForestClassifier
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_train, y_train)
y_pred = clf.predict(X_test)
acc = accuracy_score(y_test, y_pred)
st.markdown(f"Model Accuracy: {acc*100:.2f}%")

# Input from user
st.markdown("### Enter Employee Details")
input_data = {}
for f in features:
    if f in ['amount','company_tenure','age']:
        input_data[f] = st.number_input(f, min_value=0)
    else:
        input_data[f] = st.selectbox(f, options=data_model[f].unique())

# Prediction
if st.button("Predict Bonus"):
    input_df = pd.DataFrame([input_data])
    pred = clf.predict(input_df)
    st.success("✅ Will get bonus!" if pred[0]==1 else "❌ Will NOT get bonus.")

st.markdown(f"<p style='color:{pink}; font-size:12px; text-align:center;'>Made with ❤️ by Mayar</p>", unsafe_allow_html=True)
رر
