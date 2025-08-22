# utils.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px

@st.cache_data
def load_data(data_folder: str = "data"):
    """Try load CSVs from data_folder or root. Returns dict of dataframes."""
    def _safe_read(fname):
        import os
        p1 = f"{data_folder}/{fname}"
        p2 = fname
        for p in (p1, p2):
            try:
                if os.path.exists(p):
                    return pd.read_csv(p)
            except Exception:
                continue
        return pd.DataFrame()

    salary = _safe_read("salary.csv")
    employee = _safe_read("employee.csv")
    department = _safe_read("department.csv")
    title = _safe_read("title.csv")
    dept_emp = _safe_read("department_employee.csv")
    snapshot = _safe_read("current_employee_snapshot.csv")

    # normalize common variants
    if "salary" in salary.columns and "amount" not in salary.columns:
        salary = salary.rename(columns={"salary": "amount"})
    if "id" in employee.columns and "employee_id" not in employee.columns:
        employee = employee.rename(columns={"id": "employee_id"})

    # parse dates where present
    for df, cols in [
        (salary, ["from_date", "to_date"]),
        (dept_emp, ["from_date", "to_date"]),
        (title, ["from_date", "to_date"]),
        (employee, ["birth_date", "hire_date", "termination_date"]),
        (snapshot, ["birth_date", "hire_date", "termination_date"])
    ]:
        for c in cols:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce")

    # derived fields
    emp = employee.copy()
    if "employee_id" not in emp.columns:
        emp["employee_id"] = np.arange(1, len(emp) + 1)
    if "birth_date" in emp.columns:
        emp["age"] = datetime.now().year - emp["birth_date"].dt.year
    else:
        emp["age"] = np.nan
    if "hire_date" in emp.columns:
        emp["company_tenure"] = (pd.Timestamp.today() - emp["hire_date"]).dt.days / 365.25
    else:
        emp["company_tenure"] = np.nan

    return {
        "salary": salary,
        "employee": emp,
        "department": department,
        "title": title,
        "dept_emp": dept_emp,
        "snapshot": snapshot
    }

def safe_has(df, cols):
    if df is None or df.empty:
        return False
    if isinstance(cols, str):
        cols = [cols]
    return set(cols).issubset(df.columns)

def latest_per_employee(df, date_col):
    if df is None or df.empty or "employee_id" not in df.columns:
        return pd.DataFrame()
    d = df.copy()
    if date_col not in d.columns:
        d["_tmp_date"] = pd.Timestamp("1970-01-01")
        date_col = "_tmp_date"
    d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
    d = d.sort_values(["employee_id", date_col])
    return d.groupby("employee_id", as_index=False).tail(1)

def render_card(title, fig=None, table=None, description: str = None, insights: list = None, recs: list = None):
    st.markdown(f"<div style='background:rgba(255,255,255,0.02); padding:12px; border-radius:8px; margin-bottom:12px'>", unsafe_allow_html=True)
    st.subheader(title)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    if table is not None:
        st.dataframe(table, use_container_width=True)
    if description:
        st.markdown(f"**Description:** {description}")
    if insights:
        st.markdown("**Insights:**")
        for it in insights:
            st.markdown(f"- {it}")
    if recs:
        st.markdown("**Recommendations:**")
        for r in recs:
            st.markdown(f"- {r}")
    st.markdown("</div>", unsafe_allow_html=True)
