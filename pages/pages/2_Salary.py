# pages/2_Salary.py
import streamlit as st
import plotly.express as px
from utils import load_data, safe_has, render_card, latest_per_employee
import pandas as pd

data = load_data()
salary, employee, dept, title, dept_emp, snapshot = data["salary"], data["employee"], data["department"], data["title"], data["dept_emp"], data["snapshot"]

st.title("Salary & Compensation (6 charts)")

# prepare latest salary
latest = latest_per_employee(salary, "from_date") if not salary.empty else pd.DataFrame()
if "amount" in latest.columns:
    latest = latest[["employee_id","amount"]].rename(columns={"amount":"latest_salary"})
elif "latest_salary" in snapshot.columns:
    latest = snapshot[["employee_id","latest_salary"]].dropna()

# 1 Average salary over time
if safe_has(salary, ["amount","from_date"]):
    s = salary.copy()
    s["from_date"] = pd.to_datetime(s["from_date"], errors="coerce")
    s["year"] = s["from_date"].dt.year
    by = s.groupby("year")["amount"].mean().reset_index()
    if not by.empty:
        fig = px.line(by, x="year", y="amount", markers=True, title="Avg Salary Over Time")
        render_card("Avg Salary Over Time", fig, "Mean compensation per year", insights=["Trend"], recs=["Benchmark"])

# 2 Latest salary histogram
if not latest.empty:
    vals = latest.iloc[:,1].dropna()
    if not vals.empty:
        fig = px.histogram(vals, x=vals, nbins=40, title="Latest Salary Histogram")
        render_card("Latest Salary Histogram", fig, "Distribution of latest salaries", insights=["Outliers"], recs=["Review exceptions"])

# 3 Avg salary by department
if "dept_name" in snapshot.columns and not latest.empty:
    merged = snapshot.merge(latest, on="employee_id", how="left").dropna(subset=["dept_name", latest.columns[1]])
    if not merged.empty:
        by_dept = merged.groupby("dept_name")[latest.columns[1]].mean().reset_index().sort_values(by=latest.columns[1], ascending=False)
        fig = px.bar(by_dept, x="dept_name", y=latest.columns[1], title="Avg Salary by Dept")
        fig.update_xaxes(tickangle=45)
        render_card("Avg Salary by Dept", fig, "Mean pay per department", insights=["High-paying functions"], recs=["Benchmark critical roles"])

# 4 Salary spread by dept (strip)
if "dept_name" in snapshot.columns and not latest.empty:
    merged = snapshot.merge(latest, on="employee_id", how="left").dropna(subset=["dept_name", latest.columns[1]])
    if not merged.empty:
        fig = px.strip(merged, x="dept_name", y=latest.columns[1], title="Salary Spread by Dept")
        fig.update_xaxes(tickangle=45)
        render_card("Salary Spread by Dept", fig, "Point distribution of salaries", insights=["Band overlap"], recs=["Standardize ranges"])

# 5 Gender pay gap
gcol = next((c for c in ["gender","sex","Gender","Sex"] if c in snapshot.columns or c in employee.columns), None)
if gcol and not latest.empty:
    df = snapshot.merge(latest, on="employee_id", how="left").dropna(subset=[gcol, latest.columns[1]])
    if not df.empty:
        gap = df.groupby(gcol)[latest.columns[1]].mean().reset_index()
        fig = px.bar(gap, x=gcol, y=latest.columns[1], title="Avg Salary by Gender")
        render_card("Avg Salary by Gender", fig, "Mean pay per gender", insights=["Potential gaps"], recs=["Run pay equity analysis"])

# 6 Top salary growth % (employee)
if not salary.empty and {"employee_id","amount"}.issubset(salary.columns):
    g = salary.groupby("employee_id")["amount"].agg(["min","max"]).reset_index()
    g = g[g["min"]>0]
    if not g.empty:
        g["growth_pct"] = ((g["max"] - g["min"]) / g["min"]) * 100
        top = g.sort_values("growth_pct", ascending=False).head(10)
        fig = px.bar(top, x="employee_id", y="growth_pct", title="Top 10 Salary Growth %")
        render_card("Top Salary Growth %", fig, "Largest % increases", insights=["Fast-tracked"], recs=["Audit fairness"])
