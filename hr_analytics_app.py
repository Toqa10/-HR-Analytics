import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import os

# -------------------- PAGE SETUP --------------------
st.set_page_config(page_title="HR Analytics Dashboard", layout="wide")

# -------------------- SIDEBAR NAV --------------------
st.sidebar.title("Navigation")
page = st.sidebar.radio("Select Page", ["Overview", "Salary Analysis", "Department Analysis", "Employee Analysis"])

# -------------------- THEME --------------------
dark_mode = st.sidebar.checkbox("Dark Mode", value=True)
PLOTLY_TEMPLATE = "plotly_dark" if dark_mode else "plotly_white"

# -------------------- DATA LOAD --------------------
@st.cache_data
def load_csv_safe(file):
    if os.path.exists(file):
        try:
            df = pd.read_csv(file)
            if df.empty:
                st.warning(f"{file} exists but is empty.")
            return df
        except pd.errors.EmptyDataError:
            st.warning(f"{file} is empty or corrupt.")
            return pd.DataFrame()
    else:
        st.warning(f"{file} not found.")
        return pd.DataFrame()

@st.cache_data
def load_data():
    salary = load_csv_safe("salary.csv")
    employee = load_csv_safe("employee.csv")
    dept_emp = load_csv_safe("department_employee.csv")
    dept = load_csv_safe("department.csv")
    title = load_csv_safe("title.csv")
    return salary, employee, dept_emp, dept, title

salary, employee, dept_emp, dept, title = load_data()

# -------------------- HELPER FUNCTIONS --------------------
def safe_rename_id(df):
    if "employee_id" in df.columns:
        return df.copy()
    if "id" in df.columns:
        return df.rename(columns={"id":"employee_id"}).copy()
    return df.copy()

def latest_per_emp(df, date_col="to_date"):
    key_col = "employee_id" if "employee_id" in df.columns else "id"
    if key_col not in df.columns:
        return df
    df = df.rename(columns={key_col:"employee_id"})
    if date_col not in df.columns:
        df[date_col] = pd.Timestamp("1970-01-01")
    df_sorted = df.sort_values(["employee_id", date_col])
    return df_sorted.groupby("employee_id", as_index=False).tail(1)

def plot_bar(df, x, y, title):
    fig = px.bar(df, x=x, y=y, text=y)
    fig.update_layout(title=title, template=PLOTLY_TEMPLATE, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

def display_card(title, fig=None, table=None, description=""):
    st.markdown(f"### {title}")
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    if table is not None and not table.empty:
        st.dataframe(table)
        st.download_button(label="Download Table", data=table.to_csv(index=False).encode('utf-8'), file_name=f"{title.replace(' ','_')}.csv", mime='text/csv')
    if description:
        st.markdown(description)
    st.markdown("---")

# -------------------- PAGE CONTENT --------------------
if page == "Overview":
    st.title("HR Dashboard Overview")
    total_employees = len(employee)
    avg_salary = salary["amount"].mean() if "amount" in salary.columns else np.nan
    avg_tenure = (pd.Timestamp.today() - pd.to_datetime(employee["hire_date"], errors='coerce')).dt.days.mean()/365.25 if "hire_date" in employee.columns else np.nan

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Employees", total_employees)
    col2.metric("Average Salary", f"${avg_salary:,.0f}")
    col3.metric("Average Tenure (Years)", f"{avg_tenure:.1f}")

elif page == "Salary Analysis":
    st.title("Salary Analysis")
    if not salary.empty and "employee_id" in salary.columns:
        salary_latest = latest_per_emp(salary)
        display_card("Salary Distribution", fig=plot_bar(salary_latest, x="employee_id", y="amount", title="Latest Salary per Employee"), table=salary_latest)
    else:
        st.info("Salary data not available.")

elif page == "Department Analysis":
    st.title("Department Analysis")
    if not dept_emp.empty and not dept.empty:
        dept_emp_latest = latest_per_emp(dept_emp)
        dept_merge = dept_emp_latest.merge(dept, on="dept_id", how="left") if "dept_id" in dept_emp_latest.columns and "dept_id" in dept.columns else dept_emp_latest
        dept_count = dept_merge.groupby("dept_name").size().reset_index(name="count")
        display_card("Employees per Department", fig=plot_bar(dept_count, x="dept_name", y="count", title="Employees per Department"), table=dept_count)
    else:
        st.info("Department data not available.")

elif page == "Employee Analysis":
    st.title("Employee Analysis")
    if not employee.empty:
        employee_clean = safe_rename_id(employee)
        if "birth_date" in employee_clean.columns:
            employee_clean["age"] = datetime.now().year - pd.to_datetime(employee_clean["birth_date"], errors='coerce').dt.year
        display_card("Employee Ages", fig=plot_bar(employee_clean, x="employee_id", y="age", title="Employee Ages"), table=employee_clean)
    else:
        st.info("Employee data not available.")
ر
