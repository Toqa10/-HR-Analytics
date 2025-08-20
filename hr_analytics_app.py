import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# تحميل البيانات
@st.cache_data
def load_data():
    employees = pd.read_csv("employees.csv")
    departments = pd.read_csv("departments.csv")
    salaries = pd.read_csv("salary.csv")
    return employees, departments, salaries

# واجهة التطبيق
def main():
    st.set_page_config(page_title="HR Analytics", layout="wide")

    # تصميم الخلفية (لون ثابت)
    st.markdown("""
        <style>
        .stApp {
            background-color: #f0f4f8;
        }
        .card {
            background-color: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 2px 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("HR Analytics Dashboard")

    employees, departments, salaries = load_data()

    # سؤال المستخدم
    question = st.text_input("Ask an HR-related question:")

    if question:
        if "gender distribution" in question.lower():
            with st.container():
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.subheader("Gender Distribution by Department")
                gender_counts = employees.groupby(['dept_name', 'gender']).size().reset_index(name='count')

                fig, ax = plt.subplots(figsize=(8, 5))
                for gender in gender_counts['gender'].unique():
                    data = gender_counts[gender_counts['gender'] == gender]
                    ax.bar(data['dept_name'], data['count'], label=gender)

                ax.set_ylabel('Count')
                ax.set_xlabel('Department')
                ax.legend()
                plt.xticks(rotation=45)
                st.pyplot(fig)
                st.markdown('</div>', unsafe_allow_html=True)

        elif "average salary" in question.lower():
            with st.container():
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.subheader("Average Salary by Department")
                avg_salary = salaries.groupby('dept_name')['salary'].mean().reset_index()

                fig, ax = plt.subplots(figsize=(8, 5))
                ax.bar(avg_salary['dept_name'], avg_salary['salary'])
                ax.set_ylabel('Average Salary')
                ax.set_xlabel('Department')
                plt.xticks(rotation=45)
                st.pyplot(fig)
                st.markdown('</div>', unsafe_allow_html=True)

        else:
            st.warning("This question is not supported.")

if __name__ == "__main__":
    main()
