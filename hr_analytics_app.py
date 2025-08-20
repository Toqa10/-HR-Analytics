import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io

# إعدادات التصميم
st.set_page_config(page_title="HR Analytics App", layout="wide")
st.markdown("""
    <style>
        .main {
            background-color: #f5f7fa;
        }
        .card {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 2px 2px 12px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
    </style>
""", unsafe_allow_html=True)

# تحميل البيانات
@st.cache_data
def load_data():
    employees = pd.read_csv("employees.csv")
    departments = pd.read_csv("departments.csv")
    salaries = pd.read_csv("salary.csv")
    titles = pd.read_csv("titles.csv")
    return employees, departments, salaries, titles

employees, departments, salaries, titles = load_data()

st.title("HR Analytics Dashboard")
st.subheader("اسأل سؤال للحصول على Visualization")

# قائمة الأسئلة
questions = [
    "توزيع الجنس لكل قسم",
    "متوسط الرواتب لكل قسم",
    "معدل دوران الموظفين لكل قسم",
    "الفجوة بين الجنسين في الرواتب"
]

selected_question = st.selectbox("اختر سؤال:", questions)

# عرض Visualization بناءً على السؤال
if selected_question == "توزيع الجنس لكل قسم":
    gender_counts = employees.groupby(['dept_name', 'gender']).size().reset_index(name='count')
    fig, ax = plt.subplots(figsize=(8,6))
    for gender in gender_counts['gender'].unique():
        subset = gender_counts[gender_counts['gender'] == gender]
        ax.bar(subset['dept_name'], subset['count'], label=gender)
    ax.set_title('توزيع الجنس لكل قسم')
    ax.set_ylabel('عدد الموظفين')
    ax.set_xticklabels(gender_counts['dept_name'], rotation=45, ha='right')
    ax.legend()
    st.pyplot(fig)

elif selected_question == "متوسط الرواتب لكل قسم":
    merged = employees.merge(salaries, on='emp_no')
    avg_salary = merged.groupby('dept_name')['salary'].mean().sort_values()
    fig, ax = plt.subplots(figsize=(8,6))
    avg_salary.plot(kind='bar', ax=ax)
    ax.set_title('متوسط الرواتب لكل قسم')
    ax.set_ylabel('متوسط الراتب')
    st.pyplot(fig)

elif selected_question == "معدل دوران الموظفين لكل قسم":
    turnover = employees.groupby('dept_name')['status'].value_counts(normalize=True).unstack().fillna(0)
    if 'Terminated' in turnover.columns:
        turnover_rate = turnover['Terminated'] * 100
        fig, ax = plt.subplots(figsize=(8,6))
        turnover_rate.plot(kind='bar', ax=ax, color='red')
        ax.set_title('معدل دوران الموظفين لكل قسم')
        ax.set_ylabel('النسبة المئوية')
        st.pyplot(fig)
    else:
        st.warning("لا توجد بيانات كافية لحساب معدل الدوران")

elif selected_question == "الفجوة بين الجنسين في الرواتب":
    merged = employees.merge(salaries, on='emp_no')
    gender_gap = merged.groupby('gender')['salary'].mean()
    fig, ax = plt.subplots(figsize=(6,6))
    gender_gap.plot(kind='bar', ax=ax, color=['blue', 'pink'])
    ax.set_title('متوسط الرواتب حسب الجنس')
    st.pyplot(fig)

# خيار تحميل الرسوم
buf = io.BytesIO()
fig.savefig(buf, format="png")
st.download_button(
    label="تحميل الرسم كصورة",
    data=buf.getvalue(),
    file_name="visualization.png",
    mime="image/png"
)
