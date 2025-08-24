import pandas as pd
import streamlit as st
import plotly.express as px

# -------------------------
# 1. تحميل البيانات بشكل آمن
# -------------------------
@st.cache_data
def load_data():
    employee = pd.read_csv("employee.csv")
    salary = pd.read_csv("salary.csv")
    promotion = pd.read_csv("promotion.csv")

    # تحويل الأعمدة المهمة لتواريخ إن وجدت
    date_cols = ['hire_date', 'birth_date', 'termination_date', 'promotion_date']
    for col in date_cols:
        if col in employee.columns:
            employee[col] = pd.to_datetime(employee[col], errors='coerce', dayfirst=True)
        if col in promotion.columns:
            promotion[col] = pd.to_datetime(promotion[col], errors='coerce', dayfirst=True)

    return employee, salary, promotion

employee, salary, promotion = load_data()


# -------------------------
# 2. صفحة Streamlit
# -------------------------
st.set_page_config(page_title="HR Analytics Dashboard", layout="wide")
st.title("HR Analytics Dashboard")

# Sidebar Filters
st.sidebar.header("Filters")
show_demo = st.sidebar.checkbox("Show Demographics Charts", value=True)
show_salary = st.sidebar.checkbox("Show Salaries Charts", value=True)
show_promo = st.sidebar.checkbox("Show Promotions Charts", value=True)
show_retention = st.sidebar.checkbox("Show Retention Charts", value=True)


# -------------------------
# 3. Demographics Charts
# -------------------------
if show_demo:
    st.subheader("Demographics")

    # Gender distribution
    if 'gender' in employee.columns:
        gen = employee['gender'].value_counts().reset_index()
        gen.columns = ['gender','count']
        fig_gender = px.pie(gen, names='gender', values='count', title="Gender Distribution")
        st.plotly_chart(fig_gender, use_container_width=True)

    # Age distribution
    if 'birth_date' in employee.columns:
        employee['age'] = pd.Timestamp.now().year - employee['birth_date'].dt.year
        fig_age = px.histogram(employee, x='age', nbins=20, title="Age Distribution")
        st.plotly_chart(fig_age, use_container_width=True)

    # Hire year distribution
    if 'hire_date' in employee.columns:
        employee['hire_year'] = employee['hire_date'].dt.year
        fig_hire = px.histogram(employee, x='hire_year', nbins=20, title="Hire Year Distribution")
        st.plotly_chart(fig_hire, use_container_width=True)


# -------------------------
# 4. Salaries Charts
# -------------------------
if show_salary:
    st.subheader("Salaries")
    if 'salary' in salary.columns:
        fig_salary = px.histogram(salary, x='salary', nbins=20, title="Salary Distribution")
        st.plotly_chart(fig_salary, use_container_width=True)

    # Average salary by employee
    if 'employee_id' in salary.columns:
        avg_salary = salary.groupby('employee_id')['salary'].mean().reset_index()
        fig_avg_salary = px.histogram(avg_salary, x='salary', nbins=20, title="Average Salary per Employee")
        st.plotly_chart(fig_avg_salary, use_container_width=True)


# -------------------------
# 5. Promotions Charts
# -------------------------
if show_promo:
    st.subheader("Promotions")
    if 'promotion_date' in promotion.columns:
        fig_promo = px.histogram(promotion, x='promotion_date', title="Promotions Over Time")
        st.plotly_chart(fig_promo, use_container_width=True)


# -------------------------
# 6. Retention / Termination
# -------------------------
if show_retention:
    st.subheader("Retention / Termination")
    if 'termination_date' in employee.columns:
        employee['left'] = ~employee['termination_date'].isna()
        fig_ret = px.pie(employee['left'].value_counts().reset_index(), names='index', values='left',
                         title="Employee Retention vs Termination")
        st.plotly_chart(fig_ret, use_container_width=True)

    # Tenure histogram
    if 'hire_date' in employee.columns:
        employee['tenure'] = (pd.Timestamp.now() - employee['hire_date']).dt.days / 365
        fig_tenure = px.histogram(employee, x='tenure', nbins=20, title="Employee Tenure Distribution")
        st.plotly_chart(fig_tenure, use_container_width=True)
