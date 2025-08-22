import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# =============== Page Setup ===============
st.set_page_config(page_title="HR Analytics Dashboard", layout="wide")

# =============== Theme (Light / Dark) ===============
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    dark_mode = st.toggle("🌗 Dark Mode", value=True)

# Color palette (changed from pink/black to Purple + Cyan)
COLORS = {
    "primary": "#7c3aed",   # purple-600
    "accent":  "#06b6d4",   # cyan-500
    "text":    "#0f172a" if not dark_mode else "#e5e7eb",  # slate-900 / slate-200
    "bg":      "#ffffff" if not dark_mode else "#0b1021",
    "card":    "#f8fafc" if not dark_mode else "#111827",
}

PLOTLY_TEMPLATE = "plotly_dark" if dark_mode else "plotly_white"

def inject_css():
    css = f"""
    <style>
      .stApp {{
        background: {COLORS['bg']};
        color: {COLORS['text']};
      }}
      h1, h2, h3, h4, h5, h6 {{
        color: {COLORS['primary']} !important;
      }}
      .stButton>button {{
        background: linear-gradient(90deg, {COLORS['primary']} 0%, {COLORS['accent']} 100%);
        color: white; border-radius: 12px; padding: 0.5rem 1rem; border: none;
      }}
      .stSelectbox label {{
        color: {COLORS['primary']}; font-weight: 700;
      }}
      .css-1d391kg, .css-1y4p8pa {{  /* container paddings may vary across Streamlit versions */
        background: transparent !important;
      }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

inject_css()

# =============== Helpers ===============
def to_dt(s, errors="coerce"):
    return pd.to_datetime(s, errors=errors)

def latest_per_group(df, by, sort_col):
    # returns the last row per group according to sort_col
    if sort_col not in df.columns:
        df = df.copy()
        df[sort_col] = pd.Timestamp("1970-01-01")
    return df.sort_values([by, sort_col]).groupby(by, as_index=False).tail(1)

def earliest_date(*series_list):
    # first valid date across a list of date-like series
    out = None
    for s in series_list:
        if s is not None:
            out = s if out is None else out.fillna(s)
    return out

def style_fig(fig, title=None):
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["text"], size=14),
        title=dict(text=title, x=0.02, xanchor="left", y=0.95)
    )
    return fig

# =============== Data Load ===============
@st.cache_data
def load_data():
    # Read all CSVs (must be in the same folder)
    salary = pd.read_csv("salary.csv")
    employee = pd.read_csv("employee.csv")
    cur_snap = pd.read_csv("current_employee_snapshot.csv")
    department = pd.read_csv("department.csv")
    dept_emp = pd.read_csv("department_employee.csv")
    dept_mgr = pd.read_csv("department_manager.csv")  # not used but loaded for completeness
    title = pd.read_csv("title.csv")

    # --- Normalize dates if present
    for df, cols in [
        (salary, ["from_date", "to_date"]),
        (dept_emp, ["from_date", "to_date"]),
        (title, ["from_date", "to_date"]),
        (employee, ["birth_date", "hire_date"]),
    ]:
        for c in cols:
            if c in df.columns:
                df[c] = to_dt(df[c])

    # --- Build latest department per employee
    if {"employee_id", "dept_id"}.issubset(dept_emp.columns) and "dept_id" in department.columns and "dept_name" in department.columns:
        dept_latest = latest_per_group(dept_emp.merge(department, on="dept_id", how="left"),
                                       by="employee_id",
                                       sort_col="to_date" if "to_date" in dept_emp.columns else "from_date")[["employee_id", "dept_id", "dept_name"]]
    else:
        # Fallback: if current snapshot already has dept_name
        dept_latest = cur_snap[["employee_id", "dept_name"]].drop_duplicates() if "dept_name" in cur_snap.columns else pd.DataFrame(columns=["employee_id","dept_name"])

    # --- Build latest title per employee
    if {"employee_id", "title"}.issubset(title.columns):
        title_latest = latest_per_group(title, by="employee_id", sort_col="to_date" if "to_date" in title.columns else "from_date")[["employee_id", "title"]]
    else:
        title_latest = cur_snap[["employee_id", "title"]].drop_duplicates() if "title" in cur_snap.columns else pd.DataFrame(columns=["employee_id","title"])

    # --- Build latest salary per employee
    if {"employee_id", "amount"}.issubset(salary.columns):
        salary_latest = latest_per_group(salary, by="employee_id", sort_col="from_date" if "from_date" in salary.columns else "amount")[["employee_id", "amount"]].rename(columns={"amount":"latest_salary"})
    else:
        salary_latest = pd.DataFrame(columns=["employee_id","latest_salary"])

    # --- Base snapshot: one row per employee
    emp = employee.rename(columns={"id":"employee_id"}).copy()
    if "birth_date" in emp.columns:
        emp["age"] = datetime.now().year - emp["birth_date"].dt.year
    else:
        emp["age"] = np.nan

    # Compute tenure (years) if hire_date exists else from earliest assignment/salary
    tenure = pd.Series(index=emp["employee_id"], dtype=float)
    if "hire_date" in emp.columns:
        tenure = (pd.Timestamp.today() - emp["hire_date"]).dt.days/365.25
    else:
        earliest_from_dept = dept_emp.groupby("employee_id")["from_date"].min() if "from_date" in dept_emp.columns else pd.Series(dtype="datetime64[ns]")
        earliest_from_sal  = salary.groupby("employee_id")["from_date"].min() if "from_date" in salary.columns else pd.Series(dtype="datetime64[ns]")
        start = earliest_date(earliest_from_dept, earliest_from_sal)
        tenure = (pd.Timestamp.today() - start).dt.days/365.25

    emp["company_tenure"] = tenure.values

    # Merge decorations
    snapshot = (emp
                .merge(dept_latest, on="employee_id", how="left")
                .merge(title_latest, on="employee_id", how="left")
                .merge(salary_latest, on="employee_id", how="left"))

    # If current snapshot file has extra useful columns, merge them as well
    common_keys = ["employee_id"]
    extra_cols = [c for c in cur_snap.columns if c not in snapshot.columns or c in ["dept_name","title"]]  # allow overwrite of dept/title if present
    snapshot = snapshot.merge(cur_snap[common_keys + [c for c in extra_cols if c != "employee_id"]], on="employee_id", how="left")

    return salary, employee, snapshot, dept_emp, department, dept_mgr, title

salary, employee, snapshot, dept_emp, department, dept_mgr, title = load_data()

# Convenience: ensure essential columns exist
for col in ["dept_name", "title", "company_tenure", "age"]:
    if col not in snapshot.columns:
        snapshot[col] = np.nan

# =============== Header ===============
st.markdown("<h1 style='text-align:center;'>📊 HR Analytics Dashboard</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center; color:{COLORS['text']}; opacity:0.8;'>Interactive insights for workforce & compensation</p>", unsafe_allow_html=True)
st.markdown("---")

# =============== Controls ===============
options = [
    "top salaries",
    "average salary per year",
    "salary growth",
    "distribution of employee ages",
    "department with highest average salary",
    "tenure vs salary by department",
    "salary distribution by department",
    "employee distribution",
    "average salary per job title",
    "common titles by age group",
]
question = st.selectbox("Choose a business insight:", options, index=0)
center_button = st.button("✨ Show me the Insight ✨")

# =============== Insights ===============
if center_button and question:
    q = question.strip().lower()
    fig = None

    if q == "top salaries":
        if {"employee_id","amount"}.issubset(salary.columns):
            top = (salary.groupby('employee_id')['amount']
                        .max()
                        .sort_values(ascending=False)
                        .head(10)
                        .reset_index())
            top.columns = ['Employee ID', 'Top Salary']
            st.markdown("### 💰 Top 10 Salaries (Table View)")
            st.dataframe(top.style.format({'Top Salary': '{:,.0f}'}), use_container_width=True)
            st.markdown("<p style='text-align:center; opacity:0.7;'>Employees with the highest recorded salaries.</p>", unsafe_allow_html=True)
        else:
            st.error("salary.csv must contain columns: employee_id, amount")

    elif q == "average salary per year":
        if {"employee_id","amount","from_date"}.issubset(salary.columns):
            df = salary.copy()
            df["from_date"] = to_dt(df["from_date"])
            df["year"] = df["from_date"].dt.year
            avg_salary_per_year = df.groupby('year')['amount'].mean().reset_index()
            fig = px.line(avg_salary_per_year, x='year', y='amount', markers=True)
            fig.update_traces(line=dict(width=3))
            fig = style_fig(fig, "📈 Average Salary Over Time")
            st.markdown("<p style='text-align:center; opacity:0.7;'>How compensation evolves year-over-year.</p>", unsafe_allow_html=True)
        else:
            st.error("salary.csv must contain: employee_id, amount, from_date")

    elif q == "salary growth":
        if {"employee_id","amount"}.issubset(salary.columns):
            growth = salary.groupby('employee_id')['amount'].agg(['min','max']).reset_index()
            growth = growth[growth['min'] > 0]
            growth['growth_%'] = ((growth['max'] - growth['min']) / growth['min']) * 100
            top_growth = growth.sort_values('growth_%', ascending=False).head(10)
            fig = px.bar(top_growth, x='employee_id', y='growth_%', color='growth_%',
                         color_continuous_scale=px.colors.sequential.Tealgrn)
            fig = style_fig(fig, "📊 Top 10 Salary Growth %")
            st.markdown("<p style='text-align:center; opacity:0.7;'>Largest percentage increases in salary across employees.</p>", unsafe_allow_html=True)
        else:
            st.error("salary.csv must contain: employee_id, amount")

    elif q == "distribution of employee ages":
        if "age" in snapshot.columns:
            age_counts = snapshot['age'].dropna().astype(int).value_counts().sort_index().reset_index()
            age_counts.columns = ['Age', 'Count']
            fig = px.bar(age_counts, x='Count', y='Age', orientation='h',
                         color='Count', color_continuous_scale=px.colors.sequential.Purples)
            fig = style_fig(fig, "🎂 Distribution of Employee Ages")
            st.markdown("<p style='text-align:center; opacity:0.7;'>Age distribution across the current workforce.</p>", unsafe_allow_html=True)
        else:
            st.error("Age column is missing in snapshot.")

    elif q == "department with highest average salary":
        if {"employee_id","amount"}.issubset(salary.columns):
            base = snapshot[['employee_id','dept_name']].dropna(subset=['employee_id'])
            merged = base.merge(salary, on='employee_id', how='left').dropna(subset=['dept_name','amount'])
            dept_avg = (merged.groupby('dept_name')['amount']
                        .mean().reset_index()
                        .sort_values('amount', ascending=False))
            fig = px.bar(dept_avg, x='dept_name', y='amount',
                         color='amount', color_continuous_scale=px.colors.sequential.Purples)
            fig.update_xaxes(title="")
            fig = style_fig(fig, "🏢 Avg Salary per Department")
            st.markdown("<p style='text-align:center; opacity:0.7;'>Which departments command higher average compensation.</p>", unsafe_allow_html=True)
        else:
            st.error("salary.csv must contain: employee_id, amount")

    elif q == "tenure vs salary by department":
        if {"employee_id","amount"}.issubset(salary.columns):
            base = snapshot[['employee_id','company_tenure','dept_name']]
            merged = base.merge(salary[['employee_id','amount']], on='employee_id', how='left').dropna(subset=['company_tenure','amount','dept_name'])
            fig = px.scatter(merged, x='company_tenure', y='amount',
                             facet_col='dept_name', facet_col_wrap=3,
                             color='dept_name', hover_data=['employee_id'])
            fig.update_layout(height=800)
            fig = style_fig(fig, "⏳ Tenure vs Salary by Department")
            st.markdown("<p style='text-align:center; opacity:0.7;'>Relationship between years-in-company and salary for each department.</p>", unsafe_allow_html=True)
        else:
            st.error("salary.csv must contain: employee_id, amount")

    elif q == "salary distribution by department":
        if {"employee_id","amount"}.issubset(salary.columns):
            base = snapshot[['employee_id','dept_name']]
            merged = base.merge(salary[['employee_id','amount']], on='employee_id', how='left').dropna(subset=['dept_name','amount'])
            fig = px.strip(merged, x="dept_name", y="amount", color="dept_name", hover_data=["employee_id"])
            fig = style_fig(fig, "💸 Salary Distribution by Department")
            st.markdown("<p style='text-align:center; opacity:0.7;'>Spread and outliers of salaries within each department.</p>", unsafe_allow_html=True)
        else:
            st.error("salary.csv must contain: employee_id, amount")

    elif q == "employee distribution":
        if "dept_name" in snapshot.columns:
            dept_dist = snapshot['dept_name'].dropna().value_counts().reset_index()
            dept_dist.columns = ['Department', 'Count']
            fig = px.bar(dept_dist, x='Department', y='Count',
                         color='Count', color_continuous_scale=px.colors.sequential.Tealgrn)
            fig = style_fig(fig, "👥 Employee Distribution by Department")
            st.markdown("<p style='text-align:center; opacity:0.7;'>Headcount per department.</p>", unsafe_allow_html=True)
        else:
            st.error("Department names are missing.")

    elif q == "common titles by age group":
        if "age" in snapshot.columns:
            df = snapshot.copy()
            df["age_group"] = pd.cut(df["age"], bins=[10,20,30,40,50,60,70], labels=['10s','20s','30s','40s','50s','60s'], right=False)
            if "title" not in df.columns:
                df["title"] = "Unknown"
            title_counts = df.pivot_table(index='title', columns='age_group', values='employee_id', aggfunc='count', fill_value=0)
            top_titles = df['title'].value_counts().head(5).index
            title_counts_top = title_counts.loc[title_counts.index.isin(top_titles)]
            fig = go.Figure()
            for t in title_counts_top.index:
                fig.add_trace(go.Scatterpolar(
                    r=title_counts_top.loc[t].values,
                    theta=title_counts_top.columns.astype(str),
                    fill='toself', name=t
                ))
            fig.update_layout(
                polar=dict(bgcolor='rgba(0,0,0,0)',
                           radialaxis=dict(visible=True)),
            )
            fig = style_fig(fig, "🕸 Most Common Titles by Age Group (Spider Chart)")
            st.markdown("<p style='text-align:center; opacity:0.7;'>Top roles within each age segment.</p>", unsafe_allow_html=True)
        else:
            st.error("Age column is missing in snapshot.")

    elif q == "average salary per job title":
        if {"employee_id","amount"}.issubset(salary.columns):
            base = snapshot[['employee_id','title']].copy()
            base["title"] = base["title"].fillna("Unknown")
            merged = base.merge(salary[['employee_id','amount']], on='employee_id', how='left').dropna(subset=['amount'])
            avg_salary_per_title = (merged.groupby("title")["amount"].mean()
                                    .sort_values(ascending=False).reset_index())
            fig = px.bar(avg_salary_per_title.head(30), x="title", y="amount")
            fig.update_xaxes(tickangle=45, title="")
            fig = style_fig(fig, "💼 Average Salary per Job Title")
            st.markdown("<p style='text-align:center; opacity:0.7;'>Average compensation by role (top 30).</p>", unsafe_allow_html=True)
        else:
            st.error("salary.csv must contain: employee_id, amount")

    else:
        st.warning("⚠ Please select a valid question.")

    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
