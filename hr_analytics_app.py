# Home.py
import streamlit as st
import plotly.express as px
import numpy as np
from utils import load_data, safe_has, render_card

st.set_page_config(page_title="HR Analytics Dashboard", layout="wide")
data = load_data()
salary, employee, dept, title, dept_emp, snapshot = data["salary"], data["employee"], data["department"], data["title"], data["dept_emp"], data["snapshot"]

st.title("HR Analytics Dashboard — Overview")
st.markdown("Quick KPIs and high-level charts")

# KPIs
total_employees = len(employee) if not employee.empty else (len(snapshot) if not snapshot.empty else 0)
avg_salary = np.nan
if safe_has(snapshot, "latest_salary"):
    avg_salary = snapshot["latest_salary"].dropna().mean()
elif safe_has(salary, "amount") and "employee_id" in salary.columns:
    avg_salary = salary.groupby("employee_id")["amount"].last().dropna().mean()

c1, c2, c3 = st.columns(3)
c1.metric("Total Employees", f"{int(total_employees):,}")
c2.metric("Avg Latest Salary", f"${avg_salary:,.0f}" if not np.isnan(avg_salary) else "N/A")
c3.metric("Departments (known)", f"{dept['dept_id'].nunique() if not dept.empty and 'dept_id' in dept.columns else 'N/A'}")

# Overview charts (5)
# 1) hires per year
if safe_has(employee, "hire_date"):
    hires = employee.copy()
    hires["year"] = hires["hire_date"].dt.year
    hires_by = hires["year"].value_counts().sort_index().reset_index()
    hires_by.columns = ["Year", "Hires"]
    if not hires_by.empty:
        fig = px.bar(hires_by, x="Year", y="Hires", title="Hires per Year")
        render_card("Hires per Year", fig, "New hires by year", insights=["Shows hiring cycles"], recs=["Plan recruiting sprints"])

# 2) headcount by dept
if safe_has(snapshot, "dept_name"):
    d = snapshot["dept_name"].value_counts().reset_index()
    d.columns = ["Department","Headcount"]
    if not d.empty:
        fig = px.bar(d, x="Department", y="Headcount", title="Headcount by Department")
        render_card("Headcount by Department", fig, "Current headcount", insights=["Capacity hotspots"], recs=["Align hiring"])

# 3) gender mix
gcol = next((c for c in ["gender","sex","Gender","Sex"] if c in snapshot.columns or c in employee.columns), None)
if gcol:
    df = snapshot if gcol in snapshot.columns else employee
    counts = df[gcol].value_counts(dropna=False).reset_index()
    counts.columns = ["Gender","Count"]
    fig = px.pie(counts, names="Gender", values="Count", title="Gender Mix")
    render_card("Gender Mix", fig, "Overall gender composition", insights=["Track D&I"], recs=["Diversify sourcing"])

# 4) salary distribution (latest)
if safe_has(snapshot, "latest_salary") or safe_has(salary, "amount"):
    if safe_has(snapshot, "latest_salary"):
        arr = snapshot["latest_salary"].dropna()
    else:
        arr = salary.groupby("employee_id")["amount"].last().dropna() if safe_has(salary, ["employee_id","amount"]) else []
    if len(arr) > 0:
        fig = px.histogram(arr, x=arr, nbins=40, title="Latest Salary Distribution")
        render_card("Latest Salary Distribution", fig, "Distribution of latest salaries", insights=["Skew/outliers"], recs=["Review banding"])

# 5) tenure distribution
if safe_has(employee, "hire_date") or safe_has(snapshot, "company_tenure"):
    if "company_tenure" in snapshot.columns:
        arr = snapshot["company_tenure"].dropna()
    else:
        arr = employee["company_tenure"].dropna() if "company_tenure" in employee.columns else []
    if len(arr) > 0:
        fig = px.histogram(arr, x=arr, nbins=40, title="Company Tenure Distribution (yrs)")
        render_card("Tenure Distribution", fig, "Employee tenure distribution", insights=["Early churn or long-tenured core"], recs=["Target onboarding"])
