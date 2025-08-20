import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io

# ========== إعداد الصفحة ==========
st.set_page_config(
    page_title="HR Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

# CSS لتصميم الخلفية والبطاقات
st.markdown("""
    <style>
    .stApp {
        background-color: #f5f5f5;
        color: #333333;
        font-family: "Arial", sans-serif;
    }
    .card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .card h3 {
        text-align: center;
        color: #1a73e8;
    }
    </style>
""", unsafe_allow_html=True)

# ========== تحميل البيانات ==========
@st.cache_data
def load_data():
    employees = pd.read_csv("employees.csv")
    salary = pd.read_csv("salary.csv")
    dept = pd.read_csv("department.csv")
    return employees, salary, dept

employees, salary, dept = load_data()

# ========== عنوان التطبيق ==========
st.title("📊 HR Analytics Dashboard")
st.write("اكتب سؤالًا متعلقًا ببيانات الموارد البشرية للحصول على Visualization مناسب")

# ========== حقل السؤال ==========
question = st.text_input("اكتب سؤالك هنا:")

# ========== معالجة السؤال ==========
def show_gender_distribution():
    st.markdown('<div class="card"><h3>Gender Distribution per Department</h3>', unsafe_allow_html=True)
    gender_counts = employees.groupby(['dept_name', 'gender']).size().reset_index(name='count')
    fig, ax = plt.subplots(figsize=(10,6))
    sns.barplot(x='dept_name', y='count', hue='gender', data=gender_counts, ax=ax)
    plt.xticks(rotation=45)
    plt.title("Gender Distribution per Department")
    st.pyplot(fig)
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    st.download_button("Download Chart", data=buf, file_name="gender_distribution.png", mime="image/png")
    st.markdown('</div>', unsafe_allow_html=True)

def show_salary_trends():
    st.markdown('<div class="card"><h3>Salary Trends Over Time</h3>', unsafe_allow_html=True)
    salary["year"] = pd.to_datetime(salary["from_date"]).dt.year
    avg_salary = salary.groupby("year")["salary"].mean().reset_index()
    fig, ax = plt.subplots(figsize=(10,6))
    sns.lineplot(x="year", y="salary", data=avg_salary, ax=ax, marker="o")
    plt.title("Average Salary Trends")
    st.pyplot(fig)
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    st.download_button("Download Chart", data=buf, file_name="salary_trends.png", mime="image/png")
    st.markdown('</div>', unsafe_allow_html=True)

# ========== الربط مع الأسئلة ==========
if question:
    question_lower = question.lower()
    if "gender" in question_lower or "distribution" in question_lower:
        show_gender_distribution()
    elif "salary" in question_lower or "trend" in question_lower:
        show_salary_trends()
    else:
        st.warning("⚠️ هذا السؤال غير مدعوم حاليًا.")
