import streamlit as st
import pandas as pd
import plotly.express as px

# إعدادات الصفحة
st.set_page_config(page_title="HR Analytics Dashboard",
                   layout="wide",
                   page_icon="📊")

# تحميل البيانات
@st.cache_data
def load_data():
    return pd.read_csv("salary.csv")

df = load_data()

# اختيار الصفحة من الشريط الجانبي
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Overview", "Salary Insights", "Attrition Prediction"])

# تفعيل التصميم الداكن والوردي
dark_template = "plotly_dark"
main_color = "#ff4b9f"  # pink

# صفحة Overview
if page == "Overview":
    st.title("📊 HR Analytics - Overview")
    st.markdown(f"<h3 style='color:{main_color}'>General Statistics</h3>", unsafe_allow_html=True)
    st.write(f"Total Employees: {df['employee_id'].nunique()}")
    st.write(f"Total Records: {len(df)}")

# صفحة Salary Insights
elif page == "Salary Insights":
    st.title("💰 Salary Insights")
    fig = px.histogram(df, x="amount",
                       nbins=50,
                       title="Salary Distribution",
                       template=dark_template)
    fig.update_traces(marker_color=main_color)
    st.plotly_chart(fig, use_container_width=True)

# صفحة Attrition Prediction (Placeholder)
elif page == "Attrition Prediction":
    st.title("🔮 Attrition Prediction")
    st.info("This section will contain Machine Learning predictions.")

