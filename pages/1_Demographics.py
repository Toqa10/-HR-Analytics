# pages/1_Demographics.py
import streamlit as st
import plotly.express as px
from utils import load_data, safe_has, render_card
import pandas as pd

data = load_data()
salary, employee, dept, title, dept_emp, snapshot = data["salary"], data["employee"], data["department"], data["title"], data["dept_emp"], data["snapshot"]

st.title("Demographics (6 charts)")

# 1 Gender distribution
gcol = next((c for c in ["gender","sex","Gender","Sex"] if c in snapshot.columns or c in employee.columns), None)
if gcol:
    df = snapshot if gcol in snapshot.columns else employee
    counts = df[gcol].value_counts(dropna=False).reset_index()
    counts.columns = ["Gender","Count"]
    fig = px.pie(counts, names="Gender", values="Count", title="Gender Distribution")
    render_card("Gender Distribution", fig, "Gender split", insights=["D&I monitoring"], recs=["Widen sourcing"])

# 2 Age group distribution
if "age" in employee.columns or "age" in snapshot.columns:
    df = employee if "age" in employee.columns else snapshot
    a = df.dropna(subset=["age"]).copy()
    if not a.empty:
        a["age_group"] = pd.cut(a["age"], bins=[15,25,35,45,55,65,120], labels=["16-24","25-34","35-44","45-54","55-64","65+"], right=False)
        grp = a["age_group"].value_counts().sort_index().reset_index()
        grp.columns = ["Age Group","Count"]
        fig = px.bar(grp, x="Age Group", y="Count", title="Age Group Distribution")
        render_card("Age Group Distribution", fig, "Counts per age bucket", insights=["Hiring focus"], recs=["Plan benefits"])

# 3 Headcount by department
if "dept_name" in snapshot.columns:
    d = snapshot["dept_name"].value_counts().reset_index()
    d.columns = ["Department","Headcount"]
    fig = px.bar(d, x="Department", y="Headcount", title="Headcount by Department")
    render_card("Headcount by Department", fig, "Where people are", insights=["Over/understaffed"], recs=["Adjust hiring"])

# 4 Top job titles (top 15)
if "title" in snapshot.columns:
    t = snapshot["title"].fillna("Unknown").value_counts().head(15).reset_index()
    t.columns = ["Title","Count"]
    fig = px.bar(t, x="Title", y="Count", title="Top Job Titles (Top 15)")
    fig.update_xaxes(tickangle=45)
    render_card("Top Job Titles", fig, "Most common roles", insights=["Single-point dependencies"], recs=["Cross-train"])

# 5 Location (if exists)
loc_col = next((c for c in ["location","office","office_location"] if c in snapshot.columns or c in employee.columns), None)
if loc_col:
    df = snapshot if loc_col in snapshot.columns else employee
    loc = df[loc_col].value_counts().reset_index()
    loc.columns = ["Location","Count"]
    fig = px.bar(loc, x="Location", y="Count", title="Employees by Location")
    render_card("Employees by Location", fig, "Geographic spread", insights=["Concentration"], recs=["Local hiring plan"])

# 6 Employment type (if exists)
etype = next((c for c in ["employment_type","emp_type","contract_type"] if c in snapshot.columns or c in employee.columns), None)
if etype:
    df = snapshot if etype in snapshot.columns else employee
    e = df[etype].value_counts().reset_index()
    e.columns = ["Type","Count"]
    fig = px.pie(e, names="Type", values="Count", title="Employment Type")
    render_card("Employment Type", fig, "Contract/full-time split", insights=["Contract dependence"], recs=["Stabilize core roles"])
