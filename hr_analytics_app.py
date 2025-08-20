import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# إعداد صفحة التطبيق
st.set_page_config(page_title="HR Analytics Dashboard", layout="wide")

# خلفية بلون ثابت وتنسيق CSS للكروت
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f5f7fa;
    }
    .card {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    h1 {
        color: #2c3e50;
        text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# عنوان التطبيق
st.markdown("<h1>HR Analytics Dashboard</h1>", unsafe_allow_html=True)

# رفع الملفات
st.markdown("<div class='card'>", unsafe_allow_html=True)
st.subheader("Upload HR Datasets")
employee_file = st.file_uploader("Upload employee.csv", type=["csv"])
department_file = st.file_uploader("Upload department.csv", type=["csv"])
salary_file = st.file_uploader("Upload salary.csv", type=["csv"])
st.markdown("</div>", unsafe_allow_html=True)

if employee_file and department_file and salary_file:
    employees = pd.read_csv(employee_file)
    departments = pd.read_csv(department_file)
    salaries = pd.read_csv(salary_file)

    # دمج البيانات
    df = pd.merge(employees, departments, on="dept_id")
    df = pd.merge(df, salaries, on="emp_id")

    # اختيار السؤال
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Ask a Question")
    question = st.selectbox(
        "Choose an HR Insight:",
        [
            "Gender Distribution by Department",
            "Average Salary by Department",
            "Turnover Rate by Department",
            "Salary Distribution",
            "Department Headcount"
        ]
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # عرض الشارت المناسب
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Visualization")

    if question == "Gender Distribution by Department":
        gender_counts = df.groupby(['dept_name', 'gender']).size().reset_index(name='count')
        plt.figure(figsize=(10,6))
        sns.barplot(data=gender_counts, x='dept_name', y='count', hue='gender')
        plt.xticks(rotation=45)
        plt.title('Gender Distribution by Department')
        st.pyplot(plt)

    elif question == "Average Salary by Department":
        avg_salary = df.groupby('dept_name')['salary'].mean().reset_index()
        plt.figure(figsize=(10,6))
        sns.barplot(data=avg_salary, x='dept_name', y='salary', palette='coolwarm')
        plt.xticks(rotation=45)
        plt.title('Average Salary by Department')
        st.pyplot(plt)

    elif question == "Turnover Rate by Department":
        turnover = df.groupby('dept_name')['status'].apply(lambda x: (x=='Left').mean()*100).reset_index()
        plt.figure(figsize=(10,6))
        sns.barplot(data=turnover, x='dept_name', y='status', palette='magma')
        plt.xticks(rotation=45)
        plt.title('Turnover Rate by Department (%)')
        st.pyplot(plt)

    elif question == "Salary Distribution":
        plt.figure(figsize=(10,6))
        sns.histplot(df['salary'], bins=30, kde=True, color='blue')
        plt.title('Salary Distribution')
        st.pyplot(plt)

    elif question == "Department Headcount":
        headcount = df['dept_name'].value_counts().reset_index()
        headcount.columns = ['Department', 'Count']
        plt.figure(figsize=(10,6))
        sns.barplot(data=headcount, x='Department', y='Count', palette='viridis')
        plt.xticks(rotation=45)
        plt.title('Department Headcount')
        st.pyplot(plt)

    st.markdown("</div>", unsafe_allow_html=True)
