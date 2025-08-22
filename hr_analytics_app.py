import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ========================== PAGE SETUP ==========================
st.set_page_config(page_title="HR Analytics Dashboard", layout="wide")

# -------------------------- THEME SWITCH ------------------------
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    dark_mode = st.toggle("🌗 Dark Mode", value=True, help="Toggle between Dark and Light themes")
    st.caption("Tip: use the modebar on charts to download PNGs.")

PALETTE = {
    "primary": "#7c3aed",   # purple
    "accent":  "#06b6d4",   # cyan
    "text":    "#e5e7eb" if dark_mode else "#0f172a",  # slate
    "bg":      "#0b1021" if dark_mode else "#ffffff",
    "panel":   "#111827" if dark_mode else "#f8fafc",
}
PLOTLY_TEMPLATE = "plotly_dark" if dark_mode else "plotly_white"

# Inject CSS for consistent theming
st.markdown(f"""
<style>
  .stApp {{ background:{PALETTE['bg']}; color:{PALETTE['text']}; }}
  h1,h2,h3,h4,h5,h6 {{ color:{PALETTE['primary']} !important; }}
  .stButton>button {{
    background: linear-gradient(90deg, {PALETTE['primary']} 0%, {PALETTE['accent']} 100%);
    color:white; border:none; border-radius:12px; padding:.6rem 1rem; font-weight:600;
  }}
  .stSelectbox label, .stMultiSelect label {{ color:{PALETTE['primary']}; font-weight:700; }}
  .block-container {{ padding-top:1rem; }}
</style>
""", unsafe_allow_html=True)

# ========================== HELPERS =============================

def to_dt(s):
    return pd.to_datetime(s, errors="coerce")

def style_fig(fig, title=None, height=None):
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=PALETTE["text"], size=14),
        title=dict(text=title, x=0.02, xanchor="left")
    )
    if height:
        fig.update_layout(height=height)
    return fig

@st.cache_data
def latest_per_group(df, by, sort_col, ascending=True, keep="last"):
    if sort_col not in df.columns:
        df = df.copy()
        df[sort_col] = pd.Timestamp("1970-01-01")
    return (
        df.sort_values([by, sort_col], ascending=ascending)
          .groupby(by, as_index=False)
          .tail(1 if keep=="last" else 1)
    )

# ====================== LOAD & PREP DATA ========================
@st.cache_data
def load_data():
    salary = pd.read_csv("salary.csv")
    employee = pd.read_csv("employee.csv")
    cur_snap = pd.read_csv("current_employee_snapshot.csv")
    department = pd.read_csv("department.csv")
    dept_emp = pd.read_csv("department_employee.csv")
    dept_mgr = pd.read_csv("department_manager.csv")
    title = pd.read_csv("title.csv")

    # Dates normalization
    for df, cols in [
        (salary, ["from_date", "to_date"]),
        (dept_emp, ["from_date", "to_date"]),
        (title, ["from_date", "to_date"]),
        (employee, ["birth_date", "hire_date"]),
    ]:
        for c in cols:
            if c in df.columns:
                df[c] = to_dt(df[c])

    # Latest department per employee
    if {"employee_id", "dept_id"}.issubset(dept_emp.columns) and {"dept_id","dept_name"}.issubset(department.columns):
        dept_latest = (
            dept_emp.merge(department, on="dept_id", how="left")
                    .sort_values(["employee_id", dept_emp.columns[dept_emp.columns.get_loc("to_date")] if "to_date" in dept_emp.columns else "from_date"]) 
        )
        dept_latest = latest_per_group(dept_latest, by="employee_id", sort_col="to_date" if "to_date" in dept_emp.columns else "from_date")[
            ["employee_id", "dept_id", "dept_name"]
        ]
    else:
        dept_latest = cur_snap[[c for c in ["employee_id","dept_name"] if c in cur_snap.columns]].drop_duplicates()

    # Latest title per employee
    if {"employee_id", "title"}.issubset(title.columns):
        title_latest = latest_per_group(title, by="employee_id", sort_col="to_date" if "to_date" in title.columns else "from_date")[["employee_id","title"]]
    else:
        title_latest = cur_snap[[c for c in ["employee_id","title"] if c in cur_snap.columns]].drop_duplicates()

    # Latest salary per employee
    if {"employee_id","amount"}.issubset(salary.columns):
        sal_latest = latest_per_group(salary, by="employee_id", sort_col="from_date" if "from_date" in salary.columns else "amount")[["employee_id","amount"]].rename(columns={"amount":"latest_salary"})
    else:
        sal_latest = pd.DataFrame(columns=["employee_id","latest_salary"])

    # Base employees
    emp = employee.rename(columns={"id":"employee_id"}).copy()
    if "birth_date" in emp.columns:
        emp["age"] = datetime.now().year - emp["birth_date"].dt.year
    else:
        emp["age"] = np.nan

    if "hire_date" in emp.columns:
        emp["company_tenure"] = (pd.Timestamp.today() - emp["hire_date"]).dt.days/365.25
    else:
        emp["company_tenure"] = np.nan

    snapshot = (
        emp.merge(dept_latest, on="employee_id", how="left")
           .merge(title_latest, on="employee_id", how="left")
           .merge(sal_latest, on="employee_id", how="left")
    )

    # Bring over extras from current snapshot if any
    extra_cols = [c for c in cur_snap.columns if c not in snapshot.columns and c != "employee_id"]
    if extra_cols:
        snapshot = snapshot.merge(cur_snap[["employee_id"] + extra_cols], on="employee_id", how="left")

    return salary, employee, snapshot, dept_emp, department, dept_mgr, title

salary, employee, snapshot, dept_emp, department, dept_mgr, title = load_data()
for col in ["dept_name","title","company_tenure","age","latest_salary"]:
    if col not in snapshot.columns:
        snapshot[col] = np.nan

# =========================== HEADER ============================
st.markdown("""
<h1 style='text-align:center;'>📊 HR Analytics Dashboard</h1>
<p style='text-align:center; opacity:.8;'>Interactive insights for workforce & compensation</p>
""", unsafe_allow_html=True)
st.markdown("---")

# ========================= CHART PICKER ========================
ALL_CHARTS = [
    "Top salaries",
    "Average salary per year",
    "Salary growth (top 10 %)",
    "Age distribution",
    "Avg salary by department",
    "Tenure vs salary by department",
    "Salary distribution by department",
    "Headcount by department",
    "Avg salary by job title",
    "Gender ratio by department",
]

with st.sidebar:
    st.markdown("### 📈 Charts")
    selected = st.multiselect("Choose charts to display", ALL_CHARTS, default=ALL_CHARTS[:4])
    st.caption("You can pick any number of charts. They will render below in sections.")

# =========================== CHARTS ============================

# 1) Top salaries (table)
if "Top salaries" in selected:
    if {"employee_id","amount"}.issubset(salary.columns):
        top = salary.groupby('employee_id')['amount'].max().sort_values(ascending=False).head(10).reset_index()
        top.columns = ['Employee ID', 'Top Salary']
        st.subheader("💰 Top 10 Salaries")
        st.dataframe(top.style.format({'Top Salary': '{:,.0f}'}), use_container_width=True)
        st.markdown("<p style='text-align:center; opacity:.7;'>Highest recorded salary per employee.</p>", unsafe_allow_html=True)
        st.markdown("---")
    else:
        st.info("salary.csv must have employee_id, amount")

# 2) Average salary per year
if "Average salary per year" in selected:
    if {"employee_id","amount","from_date"}.issubset(salary.columns):
        df = salary.copy()
        df['from_date'] = to_dt(df['from_date'])
        df['year'] = df['from_date'].dt.year
        avg_salary_per_year = df.groupby('year')['amount'].mean().reset_index()
        fig = px.line(avg_salary_per_year, x='year', y='amount', markers=True)
        fig.update_traces(line=dict(width=3))
        st.subheader("📈 Average Salary Over Time")
        st.plotly_chart(style_fig(fig), use_container_width=True)
        st.markdown("<p style='text-align:center; opacity:.7;'>Year-over-year average compensation.</p>", unsafe_allow_html=True)
        st.markdown("---")
    else:
        st.info("salary.csv must have employee_id, amount, from_date")

# 3) Salary growth (top 10 %)
if "Salary growth (top 10 %)" in selected:
    if {"employee_id","amount"}.issubset(salary.columns):
        g = salary.groupby('employee_id')['amount'].agg(['min','max']).reset_index()
        g = g[g['min'] > 0]
        g['growth_%'] = ((g['max'] - g['min']) / g['min']) * 100
        top_growth = g.sort_values('growth_%', ascending=False).head(10)
        fig = px.bar(top_growth, x='employee_id', y='growth_%', color='growth_%', color_continuous_scale=px.colors.sequential.Tealgrn)
        st.subheader("📊 Top 10 Salary Growth %")
        st.plotly_chart(style_fig(fig), use_container_width=True)
        st.markdown("<p style='text-align:center; opacity:.7;'>Employees with the biggest salary jumps.</p>", unsafe_allow_html=True)
        st.markdown("---")
    else:
        st.info("salary.csv must have employee_id, amount")

# 4) Age distribution
if "Age distribution" in selected:
    if 'age' in snapshot.columns:
        age_counts = snapshot['age'].dropna().astype(int).value_counts().sort_index().reset_index()
        age_counts.columns = ['Age','Count']
        fig = px.bar(age_counts, x='Count', y='Age', orientation='h', color='Count', color_continuous_scale=px.colors.sequential.Purples)
        st.subheader("🎂 Distribution of Employee Ages")
        st.plotly_chart(style_fig(fig), use_container_width=True)
        st.markdown("<p style='text-align:center; opacity:.7;'>Workforce age profile.")
        st.markdown("---")
    else:
        st.info("Age column missing in snapshot")

# 5) Avg salary by department
if "Avg salary by department" in selected:
    if {"employee_id","amount"}.issubset(salary.columns):
        base = snapshot[['employee_id','dept_name']].dropna(subset=['employee_id'])
        merged = base.merge(salary[['employee_id','amount']], on='employee_id', how='left').dropna(subset=['dept_name','amount'])
        dept_avg = merged.groupby('dept_name')['amount'].mean().reset_index().sort_values('amount', ascending=False)
        fig = px.bar(dept_avg, x='dept_name', y='amount', color='amount', color_continuous_scale=px.colors.sequential.Purples)
        fig.update_xaxes(title="")
        st.subheader("🏢 Average Salary per Department")
        st.plotly_chart(style_fig(fig), use_container_width=True)
        st.markdown("<p style='text-align:center; opacity:.7;'>Which departments pay more on average.</p>", unsafe_allow_html=True)
        st.markdown("---")
    else:
        st.info("salary.csv must have employee_id, amount")

# 6) Tenure vs salary by department (facets)
if "Tenure vs salary by department" in selected:
    if {"employee_id","amount"}.issubset(salary.columns) and 'company_tenure' in snapshot.columns:
        base = snapshot[['employee_id','company_tenure','dept_name']]
        merged = base.merge(salary[['employee_id','amount']], on='employee_id', how='left').dropna(subset=['company_tenure','amount','dept_name'])
        fig = px.scatter(merged, x='company_tenure', y='amount', color='dept_name', facet_col='dept_name', facet_col_wrap=3, hover_data=['employee_id'])
        st.subheader("⏳ Tenure vs Salary by Department")
        st.plotly_chart(style_fig(fig, height=800), use_container_width=True)
        st.markdown("<p style='text-align:center; opacity:.7;'>How years-in-company relate to pay within each department.</p>", unsafe_allow_html=True)
        st.markdown("---")
    else:
        st.info("Need salary (employee_id, amount) and snapshot.company_tenure")

# 7) Salary distribution by department (strip/swarm)
if "Salary distribution by department" in selected:
    if {"employee_id","amount"}.issubset(salary.columns):
        base = snapshot[['employee_id','dept_name']]
        merged = base.merge(salary[['employee_id','amount']], on='employee_id', how='left').dropna(subset=['dept_name','amount'])
        fig = px.strip(merged, x='dept_name', y='amount', color='dept_name', hover_data=['employee_id'])
        st.subheader("💸 Salary Distribution by Department")
        st.plotly_chart(style_fig(fig), use_container_width=True)
        st.markdown("<p style='text-align:center; opacity:.7;'>Salary spread & outliers per department.</p>", unsafe_allow_html=True)
        st.markdown("---")
    else:
        st.info("salary.csv must have employee_id, amount")

# 8) Headcount by department
if "Headcount by department" in selected:
    if 'dept_name' in snapshot.columns:
        dept_dist = snapshot['dept_name'].dropna().value_counts().reset_index()
        dept_dist.columns = ['Department','Count']
        fig = px.bar(dept_dist, x='Department', y='Count', color='Count', color_continuous_scale=px.colors.sequential.Tealgrn)
        st.subheader("👥 Employee Distribution by Department")
        st.plotly_chart(style_fig(fig), use_container_width=True)
        st.markdown("<p style='text-align:center; opacity:.7;'>Headcount per department.</p>", unsafe_allow_html=True)
        st.markdown("---")
    else:
        st.info("dept_name missing in snapshot")

# 9) Avg salary by job title
if "Avg salary by job title" in selected:
    if {"employee_id","amount"}.issubset(salary.columns):
        base = snapshot[['employee_id','title']].copy()
        base['title'] = base['title'].fillna('Unknown')
        merged = base.merge(salary[['employee_id','amount']], on='employee_id', how='left').dropna(subset=['amount'])
        avg_salary_per_title = merged.groupby('title')['amount'].mean().reset_index().sort_values('amount', ascending=False)
        fig = px.bar(avg_salary_per_title.head(30), x='title', y='amount')
        fig.update_xaxes(tickangle=45, title="")
        st.subheader("💼 Average Salary by Job Title (Top 30)")
        st.plotly_chart(style_fig(fig), use_container_width=True)
        st.markdown("<p style='text-align:center; opacity:.7;'>Roles with higher/lower average compensation.</p>", unsafe_allow_html=True)
        st.markdown("---")
    else:
        st.info("salary.csv must have employee_id, amount")

# 10) Gender ratio by department (if gender exists)
if "Gender ratio by department" in selected:
    gender_col = None
    for cand in ["gender","sex","Gender","Sex"]:
        if cand in snapshot.columns:
            gender_col = cand
            break
    if gender_col and 'dept_name' in snapshot.columns:
        df = snapshot[["dept_name", gender_col]].dropna()
        if not df.empty:
            counts = df.value_counts().reset_index(name='Count')
            counts.rename(columns={gender_col:'Gender'}, inplace=True)
            fig = px.bar(counts, x='dept_name', y='Count', color='Gender', barmode='stack')
            st.subheader("🚻 Gender Ratio by Department")
            st.plotly_chart(style_fig(fig), use_container_width=True)
            st.markdown("<p style='text-align:center; opacity:.7;'>Gender composition across departments.</p>", unsafe_allow_html=True)
            st.markdown("---")
        else:
            st.info("No gender data available")
    else:
        st.info("Gender or dept_name column not found in snapshot")

st.success("✅ Render complete. Use the sidebar to toggle theme and select charts.")
