import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# ========================== PAGE SETUP ==========================
st.set_page_config(page_title="HR Analytics Dashboard", layout="wide")

# -------------------------- THEME SWITCH ------------------------
with st.sidebar:
    st.markdown("## ⚙ Settings")
    dark = st.toggle("🌗 Dark Mode", value=True)

PLOTLY_TEMPLATE = "plotly_dark" if dark else "plotly_white"
UI_TEXT = "#e5e7eb" if dark else "#0f172a"
UI_BG = "#0b1021" if dark else "#ffffff"
UI_PANEL = "#111827" if dark else "#f8fafc"

PALETTES = {
    "demo": {"seq": px.colors.sequential.Blues,  "primary": "#0284c7"},
}

st.markdown(f"""
<style>
  .stApp {{ background:{UI_BG}; color:{UI_TEXT}; }}
  .card {{ background:{UI_PANEL}; border-radius:16px; padding:1rem; margin-bottom:1rem; }}
  h1,h2,h3 {{ color:#cbd5e1 !important; }}
  .muted {{ opacity:.85; }}
  .notes b {{ color:#cbd5e1; }}
</style>
""", unsafe_allow_html=True)

# ============================ HELPERS ===========================
def to_dt(s):
    return pd.to_datetime(s, errors="coerce")

@st.cache_data
def load_data():
    # استخدم head(5000) لتقليل الحجم
    salary = pd.read_csv("salary.csv").head(5000)
    employee = pd.read_csv("employee.csv").head(5000)
    snap = pd.read_csv("current_employee_snapshot.csv").head(5000)
    dept = pd.read_csv("department.csv").head(5000)
    dept_emp = pd.read_csv("department_employee.csv").head(5000)
    dept_mgr = pd.read_csv("department_manager.csv").head(5000)
    title = pd.read_csv("title.csv").head(5000)

    # تحويل التواريخ
    for df, cols in [
        (salary, ["from_date","to_date"]),
        (dept_emp,["from_date","to_date"]),
        (title,   ["from_date","to_date"]),
        (employee,["birth_date","hire_date","termination_date"]),
    ]:
        for c in cols:
            if c in df.columns: df[c] = to_dt(df[c])

    # employee base
    emp = employee.copy()
    if "birth_date" in emp.columns:
        emp["age"] = datetime.now().year - emp["birth_date"].dt.year
    else:
        emp["age"] = np.nan
    if "hire_date" in emp.columns:
        emp["company_tenure"] = (pd.Timestamp.today() - emp["hire_date"]).dt.days/365.25
    else:
        emp["company_tenure"] = np.nan

    # latest dept/title/salary
    if {'employee_id','dept_id'}.issubset(dept_emp.columns) and {'dept_id','dept_name'}.issubset(dept.columns):
        d_latest = dept_emp.merge(dept, on="dept_id", how="left")[['employee_id','dept_name']]
    else:
        d_latest = snap[['employee_id','dept_name']].drop_duplicates()

    if {'employee_id','title'}.issubset(title.columns):
        t_latest = title[['employee_id','title']].drop_duplicates()
    else:
        t_latest = snap[['employee_id','title']].drop_duplicates()

    if {'employee_id','amount'}.issubset(salary.columns):
        s_latest = salary[['employee_id','amount']].rename(columns={'amount':'latest_salary'})
    else:
        s_latest = pd.DataFrame(columns=["employee_id","latest_salary"])

    snapshot = emp.merge(d_latest, on="employee_id", how="left")\
                  .merge(t_latest, on="employee_id", how="left")\
                  .merge(s_latest, on="employee_id", how="left")

    return snapshot

snapshot = load_data()

for col in ["dept_name","title","company_tenure","age","latest_salary"]:
    if col not in snapshot.columns: snapshot[col] = np.nan

# ============================ HEADER ===========================
st.markdown("""
<h1 style='text-align:center;'>📊 HR Analytics Dashboard</h1>
<p style='text-align:center;' class='muted'>Demographics Overview</p>
""", unsafe_allow_html=True)
st.markdown("---")

# ========================= SIDEBAR NAVIGATION ===================
tab = st.sidebar.radio("Go to:", ["Demographics"])

# ========================= DEMOGRAPHICS =========================
if tab=="Demographics":
    pal = PALETTES['demo']

    # 1 Age histogram
    if 'age' in snapshot.columns:
        df = snapshot.dropna(subset=['age'])
        if not df.empty:
            fig = px.histogram(df, x='age', nbins=30, color_discrete_sequence=[pal['primary']])
            st.markdown("<div class='card'><h3>🎂 Age Distribution</h3></div>", unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True)

    # 2 Headcount by dept
    if 'dept_name' in snapshot.columns:
        dep = snapshot['dept_name'].value_counts().reset_index()
        dep.columns = ['Department','Headcount']
        fig = px.bar(dep, x='Department', y='Headcount', color='Headcount', color_continuous_scale=pal['seq'])
        st.markdown("<div class='card'><h3>👥 Headcount by Department</h3></div>", unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)

    # 3 Gender overall
    gcol = next((c for c in ["gender","sex"] if c in snapshot.columns), None)
    if gcol:
        overall = snapshot[gcol].value_counts().reset_index()
        overall.columns=['Gender','Count']
        fig = px.pie(overall, names='Gender', values='Count')
        st.markdown("<div class='card'><h3>🚻 Gender Mix (Overall)</h3></div>", unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)

    # 4 Age vs Tenure heatmap
    if {'age','company_tenure'}.issubset(snapshot.columns):
        fig = px.density_heatmap(snapshot.dropna(subset=['age','company_tenure']), x='age', y='company_tenure', nbinsx=20, nbinsy=20, color_continuous_scale=pal['seq'])
        st.markdown("<div class='card'><h3>🔥 Age × Tenure (Heat)</h3></div>", unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)
