import streamlit as st
import pandas as pd

st.set_page_config(page_title="HR Analytics Dashboard", layout="wide")

st.title("HR Analytics Dashboard")
st.markdown("### Overview")
st.info("""
Welcome to the HR Analytics Dashboard.  
Navigate through the pages on the left sidebar to explore:
- Demographics
- Salary Analysis
- Turnover
- Promotions
""")

@st.cache_data
def load_data():
    dfE = pd.read_csv("data/employee.csv")
    dfS = pd.read_csv("data/salary.csv")
    dfD = pd.read_csv("data/department.csv")
    dfT = pd.read_csv("data/title.csv")
    return dfE, dfS, dfD, dfT

dfE, dfS, dfD, dfT = load_data()

st.metric("Total Employees", len(dfE))
st.metric("Total Departments", dfD["dept_id"].nunique())
st.metric("Average Salary", f"${dfS['salary'].mean():,.2f}")
