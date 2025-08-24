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
    st.markdown("## ⚙ Settings")
    dark = st.toggle("🌗 Dark Mode", value=True)

PLOTLY_TEMPLATE = "plotly_dark" if dark else "plotly_white"
UI_TEXT = "#e5e7eb" if dark else "#0f172a"
UI_BG = "#0b1021" if dark else "#ffffff"
UI_PANEL = "#111827" if dark else "#f8fafc"

PALETTES = {
    "demo": {"seq": px.colors.sequential.Blues,  "primary": "#0284c7", "accent": "#06b6d4"},
    "pay":  {"seq": px.colors.sequential.Greens, "primary": "#16a34a", "accent": "#84cc16"},
    "promo":{"seq": px.colors.sequential.Purples,"primary": "#7c3aed", "accent": "#ec4899"},
    "ret":  {"seq": px.colors.sequential.OrRd,   "primary": "#f97316", "accent": "#ef4444"},
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
def latest_per_emp(df, sort_col):
    if sort_col not in df.columns:
        df = df.copy(); df[sort_col] = pd.Timestamp("1970-01-01")
    key = 'employee_id' if 'employee_id' in df.columns else ('id' if 'id' in df.columns else None)
    if key is None:
        return df
    return df.rename(columns={key:'employee_id'})\
             .sort_values(["employee_id", sort_col])\
             .groupby("employee_id", as_index=False).tail(1)

def fig_style(fig, title=None):
    fig.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    if title:
        fig.update_layout(title=dict(text=title, x=0.02, xanchor="left"))
    return fig

def card(title: str, fig=None, table: pd.DataFrame|None=None, desc:str="", insights:list[str]|None=None, recs:list[str]|None=None):
    st.markdown(f"<div class='card'><h3>{title}</h3>", unsafe_allow_html=True)

    # --- الرسم البياني ---
    if fig is not None:
        st.plotly_chart(fig_style(fig), use_container_width=True)

    # --- الجدول + زر التحميل ---
    if table is not None:
        st.dataframe(table, use_container_width=True)
        st.download_button(
            label="⬇ Download Table as CSV",
            data=table.to_csv(index=False),
            file_name=f"{title.replace(' ','_')}.csv",
            mime="text/csv"
        )
        # زر تفاعلي مثال: تسليط الضوء على أكبر قيمة في العمود الأول بعد ID
        if st.button(f"✨ Highlight Max ({title})"):
            col = table.columns[1] if len(table.columns) > 1 else table.columns[0]
            max_val = table[col].max()
            st.markdown(f"**Max {col}: {max_val}**")

    # --- الوصف، insights، recommendations ---
    if desc or insights or recs:
        st.markdown("<div class='notes'>", unsafe_allow_html=True)
        if desc: st.markdown(f"Description: {desc}")
        if insights:
            st.markdown("Insights:")
            for i in insights: st.markdown(f"- {i}")
        if recs:
            st.markdown("Recommendations:")
            for r in recs: st.markdown(f"- {r}")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

def has_cols(df: pd.DataFrame, cols: list[str]) -> bool:
    return set(cols).issubset(df.columns)

def safe_rename_id(df: pd.DataFrame) -> pd.DataFrame:
    if 'employee_id' in df.columns:
        return df.copy()
    if 'id' in df.columns:
        return df.rename(columns={'id':'employee_id'}).copy()
    return df.copy()

# ======================== LOAD & PREP DATA ======================
@st.cache_data
def load_data():
    salary = pd.read_csv("salary.csv")
    employee = pd.read_csv("employee.csv")
    snap = pd.read_csv("current_employee_snapshot.csv")
    dept = pd.read_csv("department.csv")
    dept_emp = pd.read_csv("department_employee.csv")
    dept_mgr = pd.read_csv("department_manager.csv")
    title = pd.read_csv("title.csv")

    # تحويل التواريخ
    for df, cols in [
        (salary, ["from_date","to_date"]),
        (dept_emp,["from_date","to_date"]),
        (title,   ["from_date","to_date"]),
        (employee,["birth_date","hire_date","termination_date"]),
    ]:
        for c in cols:
            if c in df.columns: df[c] = to_dt(df[c])

    # إعداد بيانات الموظفين الأساسية
    emp = safe_rename_id(employee)
    if "birth_date" in emp.columns:
        emp["age"] = datetime.now().year - to_dt(emp["birth_date"]).dt.year
    else:
        emp["age"] = np.nan
    if "hire_date" in emp.columns:
        emp["company_tenure"] = (pd.Timestamp.today() - to_dt(emp["hire_date"])).dt.days/365.25
    else:
        emp["company_tenure"] = np.nan

    # أحدث قسم/وظيفة/راتب
    dept_emp = safe_rename_id(dept_emp)
    dept = dept.copy()
    if {"employee_id","dept_id"}.issubset(dept_emp.columns) and {"dept_id","dept_name"}.issubset(dept.columns):
        d_latest = latest_per_emp(dept_emp, "to_date" if "to_date" in dept_emp.columns else "from_date").merge(dept, on="dept_id", how="left")
        d_latest = d_latest[["employee_id","dept_name"]]
    else:
        d_latest = snap[[c for c in ["employee_id","dept_name","id"] if c in snap.columns]].copy()
        d_latest = safe_rename_id(d_latest)[["employee_id","dept_name"]].drop_duplicates()

    title = safe_rename_id(title)
    if {"employee_id","title"}.issubset(title.columns):
        t_latest = latest_per_emp(title, "to_date" if "to_date" in title.columns else "from_date")[['employee_id','title']]
    else:
        t_latest = snap[[c for c in ["employee_id","title","id"] if c in snap.columns]].copy()
        t_latest = safe_rename_id(t_latest)[["employee_id","title"]].drop_duplicates()

    salary = safe_rename_id(salary)
    if {"employee_id","amount"}.issubset(salary.columns):
        s_latest = latest_per_emp(salary, "from_date")[['employee_id','amount']].rename(columns={'amount':'latest_salary'})
    else:
        s_latest = pd.DataFrame(columns=["employee_id","latest_salary"])

    snapshot = emp.merge(d_latest, on="employee_id", how="left")\
                  .merge(t_latest, on="employee_id", how="left")\
                  .merge(s_latest, on="employee_id", how="left")

    # إضافات من الـ snapshot
    snap = safe_rename_id(snap)
    extras = [c for c in snap.columns if c not in snapshot.columns and c != 'employee_id']
    if extras:
        snapshot = snapshot.merge(snap[["employee_id"]+extras], on="employee_id", how="left")

    return salary, employee, snapshot, dept_emp, dept, dept_mgr, title

salary, employee, snapshot, dept_emp, dept, dept_mgr, title = load_data()
for col in ["dept_name","title","company_tenure","age","latest_salary"]:
    if col not in snapshot.columns: snapshot[col] = np.nan

# ============================ HEADER ===========================
st.markdown("""
<h1 style='text-align:center;'>📊 HR Analytics Dashboard</h1>
<p style='text-align:center;' class='muted'>30 interactive charts across Demographics, Salaries, Promotions, and Retention. Each chart includes Description, Insights, and Recommendations.</p>
""", unsafe_allow_html=True)
st.markdown("---")

# ============================== TABS ===========================
d1, d2, d3, d4 = st.tabs([
    "👤 Demographics (8)",
    "💵 Salaries & Compensation (8)",
    "🚀 Promotions & Career Growth (7)",
    "🧲 Retention & Turnover (7)",
])

# ========================= DEMOGRAPHICS (8) ====================
with d1:
    pal = PALETTES['demo']
    if 'age' in snapshot.columns:
        df = snapshot.dropna(subset=['age'])
        if not df.empty:
            fig = px.histogram(df, x='age', nbins=40, color_discrete_sequence=[pal['primary']])
            card("🎂 Age Distribution", fig,
                 desc="Histogram of employees' ages.",
                 insights=["Highlights dominant age bands and outliers."],
                 recs=["Tailor L&D and benefits by age clusters."])
# بقية كروت DEMOGRAPHICS... نفس الأسلوب، تضيف كل كارت بالجدول أو الرسم البياني

# ========================= SALARY / PAY ========================
with d2:
    pal = PALETTES['pay']
    if 'latest_salary' in snapshot.columns:
        df = snapshot[['employee_id','latest_salary','dept_name']].dropna()
        if not df.empty:
            fig = px.box(df, x='dept_name', y='latest_salary', color='dept_name', color_discrete_sequence=pal['seq'])
            card("💰 Salary by Department", fig, df,
                 desc="Distribution of latest salaries by department.",
                 insights=["Identify high/low paying departments."],
                 recs=["Adjust pay structure to reduce inequity."])

# ========================= PROMOTIONS / CAREER =================
with d3:
    pal = PALETTES['promo']
    if 'title' in snapshot.columns and 'employee_id' in snapshot.columns:
        df = snapshot.groupby('title')['employee_id'].count().reset_index().rename(columns={'employee_id':'count'})
        fig = px.bar(df, x='title', y='count', color='count', color_continuous_scale=pal['seq'])
        card("🚀 Employees per Title", fig, df,
             desc="Counts of employees per job title.",
             insights=["Highlights concentration of workforce."],
             recs=["Plan succession and talent development."])

# ========================= RETENTION / TURNOVER ================
with d4:
    pal = PALETTES['ret']
    if 'termination_date' in snapshot.columns:
        df = snapshot.dropna(subset=['termination_date'])
        if not df.empty:
            df['year'] = df['termination_date'].dt.year
            df_count = df.groupby('year')['employee_id'].count().reset_index().rename(columns={'employee_id':'leavers'})
            fig = px.line(df_count, x='year', y='leavers', markers=True, color_discrete_sequence=[pal['primary']])
            card("🧲 Annual Employee Turnover", fig, df_count,
                 desc="Trend of employee turnover per year.",
                 insights=["Identify spikes in attrition."],
                 recs=["Investigate causes and improve retention."])
