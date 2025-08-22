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
    st.caption("اختر التبويب وشاهد الوصف + الاستنتاجات + التوصيات تحت كل شارت")

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
    return df.sort_values(["employee_id", sort_col]).groupby("employee_id", as_index=False).tail(1)

def fig_style(fig, title=None):
    fig.update_layout(template=PLOTLY_TEMPLATE, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    if title:
        fig.update_layout(title=dict(text=title, x=0.02, xanchor="left"))
    return fig

def card(title: str, fig=None, table: pd.DataFrame|None=None, desc:str="", insights:list[str]|None=None, recs:list[str]|None=None):
    st.markdown(f"<div class='card'><h3>{title}</h3>", unsafe_allow_html=True)
    if fig is not None:
        st.plotly_chart(fig_style(fig), use_container_width=True)
    if table is not None:
        st.dataframe(table, use_container_width=True)
    if desc or insights or recs:
        st.markdown("<div class='notes'>", unsafe_allow_html=True)
        if desc: st.markdown(f"*Description:* {desc}")
        if insights:
            st.markdown("*Insights:*")
            for i in insights: st.markdown(f"- {i}")
        if recs:
            st.markdown("*Recommendations:*")
            for r in recs: st.markdown(f"- {r}")
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

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

    # dates
    for df, cols in [
        (salary, ["from_date","to_date"]),
        (dept_emp,["from_date","to_date"]),
        (title,   ["from_date","to_date"]),
        (employee,["birth_date","hire_date","termination_date"]),
    ]:
        for c in cols:
            if c in df.columns: df[c] = to_dt(df[c])

    # base
    emp = employee.rename(columns={"id":"employee_id"}).copy()
    if "birth_date" in emp.columns:
        emp["age"] = datetime.now().year - emp["birth_date"].dt.year
    else:
        emp["age"] = np.nan
    if "hire_date" in emp.columns:
        emp["company_tenure"] = (pd.Timestamp.today() - emp["hire_date"]).dt.days/365.25
    else:
        emp["company_tenure"] = np.nan

    # latest dept/title/salary
    if {"employee_id","dept_id"}.issubset(dept_emp.columns) and {"dept_id","dept_name"}.issubset(dept.columns):
        d_latest = latest_per_emp(dept_emp, "to_date" if "to_date" in dept_emp.columns else "from_date").merge(dept, on="dept_id", how="left")
        d_latest = d_latest[["employee_id","dept_name"]]
    else:
        d_latest = snap[[c for c in ["employee_id","dept_name"] if c in snap.columns]].drop_duplicates()

    if {"employee_id","title"}.issubset(title.columns):
        t_latest = latest_per_emp(title, "to_date" if "to_date" in title.columns else "from_date")[['employee_id','title']]
    else:
        t_latest = snap[[c for c in ["employee_id","title"] if c in snap.columns]].drop_duplicates()

    if {"employee_id","amount"}.issubset(salary.columns):
        s_latest = latest_per_emp(salary, "from_date")[['employee_id','amount']].rename(columns={'amount':'latest_salary'})
    else:
        s_latest = pd.DataFrame(columns=["employee_id","latest_salary"])

    snapshot = emp.merge(d_latest, on="employee_id", how="left")\
                  .merge(t_latest, on="employee_id", how="left")\
                  .merge(s_latest, on="employee_id", how="left")

    # bring extras from current snapshot
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
    # 1 Age histogram
    if 'age' in snapshot.columns:
        df = snapshot.dropna(subset=['age'])
        fig = px.histogram(df, x='age', nbins=40, color_discrete_sequence=[pal['primary']])
        card("🎂 Age Distribution", fig,
             desc="Histogram of employees' ages.",
             insights=["Highlights dominant age bands and outliers."],
             recs=["Tailor L&D and benefits by age clusters."])

    # 2 Age groups by dept (stack)
    if {'age','dept_name'}.issubset(snapshot.columns):
        tmp = snapshot.copy(); tmp['age_group'] = pd.cut(tmp['age'], [10,20,30,40,50,60,70], labels=['10s','20s','30s','40s','50s','60s'], right=False)
        pivot = tmp.pivot_table(index='dept_name', columns='age_group', values='employee_id', aggfunc='count', fill_value=0).reset_index()
        fig = px.bar(pivot, x='dept_name', y=pivot.columns[1:], barmode='stack', color_discrete_sequence=pal['seq'])
        fig.update_xaxes(tickangle=45)
        card("🏢 Age Group Composition by Department", fig,
             desc="Stacked headcount by age group.",
             insights=["Detect departments with skewed demographics."],
             recs=["Balance hiring to reduce succession risk."])

    # 3 Headcount by dept
    if 'dept_name' in snapshot.columns:
        dep = snapshot['dept_name'].value_counts().reset_index()
        dep.columns = ['Department','Headcount']
        fig = px.bar(dep, x='Department', y='Headcount', color='Headcount', color_continuous_scale=pal['seq'])
        card("👥 Headcount by Department", fig,
             desc="Current headcount per department.",
             insights=["Capacity hotspots and understaffed teams."],
             recs=["Align hiring with demand and revenue impact."])

    # 4 Title headcount (Top 20)
    if 'title' in snapshot.columns:
        t = snapshot['title'].fillna('Unknown').value_counts().head(20).reset_index()
        t.columns = ['Title','Headcount']
        fig = px.bar(t, x='Title', y='Headcount', color='Headcount', color_continuous_scale=pal['seq'])
        fig.update_xaxes(tickangle=45)
        card("🏷 Top 20 Titles by Headcount", fig,
             desc="Most common roles.",
             insights=["Identify critical roles and single points of failure."],
             recs=["Cross-train & succession planning for critical titles."])

    # 5 Age by dept (box)
    if {'age','dept_name'}.issubset(snapshot.columns):
        fig = px.box(snapshot.dropna(subset=['age','dept_name']), x='dept_name', y='age', color='dept_name')
        fig.update_xaxes(tickangle=45, title="")
        card("📦 Age by Department (Box)", fig,
             desc="Spread & median age by department.",
             insights=["Outliers suggest tailored wellbeing programs."],
             recs=["Review workload design in teams with wide age spread."])

    # 6 Gender overall + 7 by dept
    gcol = next((c for c in ["gender","sex","Gender","Sex"] if c in snapshot.columns), None)
    if gcol:
        overall = snapshot[gcol].value_counts().reset_index(); overall.columns=['Gender','Count']
        fig = px.pie(overall, names='Gender', values='Count')
        card("🚻 Gender Mix (Overall)", fig,
             desc="Gender composition company-wide.",
             insights=["Imbalances vs targets."],
             recs=["Expand sourcing & ensure unbiased screening."])
        if 'dept_name' in snapshot.columns:
            gdept = snapshot[[gcol,'dept_name']].dropna().value_counts().reset_index(name='Count').rename(columns={gcol:'Gender'})
            fig = px.bar(gdept, x='dept_name', y='Count', color='Gender', barmode='stack')
            card("🚻 Gender Ratio by Department", fig,
                 desc="Gender distribution per department.",
                 insights=["Surfacing most skewed units."],
                 recs=["Local goals & mentorship for underrepresented groups."])

    # 8 Age vs Tenure heatmap
    if {'age','company_tenure'}.issubset(snapshot.columns):
        fig = px.density_heatmap(snapshot.dropna(subset=['age','company_tenure']), x='age', y='company_tenure', nbinsx=20, nbinsy=20, color_continuous_scale=pal['seq'])
        card("🔥 Age × Tenure (Heat)", fig,
             desc="Density across age and tenure.",
             insights=["Clusters reveal career stage concentrations."],
             recs=["Design stage‑specific L&D and retention programs."])

# ==================== SALARIES & COMPENSATION (8) ==============
with d2:
    pal = PALETTES['pay']

    # prepare latest salary
    latest_sal = latest_per_emp(salary, 'from_date') if {'employee_id','amount'}.issubset(salary.columns) else None

    # 1 Avg salary per year
    if {'employee_id','amount','from_date'}.issubset(salary.columns):
        s = salary.copy(); s['from_date'] = to_dt(s['from_date']); s['year'] = s['from_date'].dt.year
        avg = s.groupby('year')['amount'].mean().reset_index()
        fig = px.line(avg, x='year', y='amount', markers=True)
        card("📈 Average Salary Over Time", fig,
             desc="Year‑over‑year average compensation.",
             insights=["Acceleration or stagnation in pay growth."],
             recs=["Budget merit increases aligned with market."])

    # 2 Top 20 salaries (table)
    if {'employee_id','amount'}.issubset(salary.columns):
        top = salary.groupby('employee_id')['amount'].max().sort_values(ascending=False).head(20).reset_index()
        top.columns = ['Employee ID','Top Salary']
        card("💰 Top 20 Salaries (Table)", None, top.style.format({'Top Salary':'{:,.0f}'}).data,
             desc="Highest recorded salary per employee.",
             insights=["Executive bands and outliers."],
             recs=["Ensure pay governance & internal parity."])

    # 3 Salary histogram (latest)
    if latest_sal is not None:
        fig = px.histogram(latest_sal, x='amount', nbins=40, color_discrete_sequence=[pal['primary']])
        card("📦 Salary Distribution (Latest)", fig,
             desc="Histogram of latest salary amounts.",
             insights=["Skewness; band compression or outliers."],
             recs=["Review ranges; consider mid‑point corrections."])

    # 4 Avg salary by department
    if latest_sal is not None and 'dept_name' in snapshot.columns:
        m = snapshot[['employee_id','dept_name']].merge(latest_sal[['employee_id','amount']], on='employee_id', how='left').dropna()
        g = m.groupby('dept_name')['amount'].mean().reset_index().sort_values('amount', ascending=False)
        fig = px.bar(g, x='dept_name', y='amount', color='amount', color_continuous_scale=pal['seq'])
        fig.update_xaxes(tickangle=45)
        card("🏢 Average Salary by Department", fig,
             desc="Mean latest compensation per department.",
             insights=["High‑paying functions vs support units."],
             recs=["Benchmark vs market; adjust critical roles."])

    # 5 Tenure vs salary (scatter)
    if latest_sal is not None and 'company_tenure' in snapshot.columns:
        m = snapshot[['employee_id','company_tenure']].merge(latest_sal[['employee_id','amount']], on='employee_id', how='left').dropna()
        fig = px.scatter(m, x='company_tenure', y='amount')
        card("⏳ Tenure vs Salary", fig,
             desc="Relationship between tenure and pay.",
             insights=["Weak link may indicate pay policy issues."],
             recs=["Define progression bands tied to tenure & performance."])

    # 6 Salary growth top 10
    if {'employee_id','amount'}.issubset(salary.columns):
        g = salary.groupby('employee_id')['amount'].agg(['min','max']).reset_index(); g = g[g['min']>0]
        g['growth_%'] = ((g['max']-g['min'])/g['min'])*100
        topg = g.sort_values('growth_%', ascending=False).head(10)
        fig = px.bar(topg, x='employee_id', y='growth_%', color='growth_%', color_continuous_scale=pal['seq'])
        card("🚀 Top 10 Salary Growth %", fig,
             desc="Largest % increase from first to latest salary.",
             insights=["Fast‑trackers or compression fixes."],
             recs=["Audit fairness; align to performance."])

    # 7 Salary spread by department (strip)
    if latest_sal is not None and 'dept_name' in snapshot.columns:
        m = snapshot[['employee_id','dept_name']].merge(latest_sal[['employee_id','amount']], on='employee_id', how='left').dropna()
        fig = px.strip(m, x='dept_name', y='amount', color='dept_name')
        fig.update_xaxes(tickangle=45)
        card("💸 Salary Spread by Department", fig,
             desc="Point distribution of latest salaries per department.",
             insights=["Outliers and range overlaps."],
             recs=["Standardize ranges; guardrails for exceptions."])

    # 8 Avg salary by title (Top 30)
    if latest_sal is not None and 'title' in snapshot.columns:
        m = snapshot[['employee_id','title']].merge(latest_sal[['employee_id','amount']], on='employee_id', how='left').dropna()
        g = m.groupby('title')['amount'].mean().reset_index().sort_values('amount', ascending=False).head(30)
        fig = px.bar(g, x='title', y='amount')
        fig.update_xaxes(tickangle=45, title="")
        card("💼 Average Salary by Title (Top 30)", fig,
             desc="Mean latest pay for top titles.",
             insights=["Premium roles and pay gaps."],
             recs=["Run pay‑equity analysis within similar bands."])

# ================= PROMOTIONS & CAREER GROWTH (7) ==============
with d3:
    pal = PALETTES['promo']
    promos_ready = {"employee_id","title","from_date"}.issubset(title.columns)

    if promos_ready:
        tdf = title.copy(); tdf['from_date'] = to_dt(tdf['from_date'])
        tdf = tdf.sort_values(['employee_id','from_date'])
        tdf['prev_title'] = tdf.groupby('employee_id')['title'].shift()
        tdf['changed'] = (tdf['title'] != tdf['prev_title']).astype(int)
        tdf['year'] = tdf['from_date'].dt.year
        promos = tdf.groupby('employee_id')['changed'].sum().reset_index(name='promotion_count')

        # 1 Promotions per year
        per_year = tdf[tdf['changed']==1].groupby('year').size().reset_index(name='Promotions')
        fig = px.bar(per_year, x='year', y='Promotions', color='Promotions', color_continuous_scale=pal['seq'])
        card("📅 Promotions per Year", fig,
             desc="Count of title changes by year.",
             insights=["Waves of career moves; hiring vs promotion strategy."],
             recs=["Stabilize cadence with clear career frameworks."])

        # 2 Time to first promotion
        if 'hire_date' in employee.columns:
            first_change = tdf[tdf['changed']==1].groupby('employee_id')['from_date'].min().reset_index().rename(columns={'from_date':'first_promo_date'})
            tmp = employee.rename(columns={'id':'employee_id'})[['employee_id','hire_date']].merge(first_change, on='employee_id', how='inner')
            tmp['time_to_first_promo_years'] = (to_dt(tmp['first_promo_date']) - to_dt(tmp['hire_date'])).dt.days/365.25
            fig = px.histogram(tmp, x='time_to_first_promo_years', nbins=30, color_discrete_sequence=[pal['primary']])
            card("⏱ Time to First Promotion (Years)", fig,
                 desc="Distribution of tenure before first promotion.",
                 insights=["Long lags may harm retention of top talent."],
                 recs=["Publish SLA for timelines & criteria."])

        # 3 Promotions by department
        if 'dept_name' in snapshot.columns:
            pmap = promos.merge(snapshot[['employee_id','dept_name']], on='employee_id', how='left')
            by_dept = pmap.groupby('dept_name')['promotion_count'].sum().reset_index().sort_values('promotion_count', ascending=False)
            fig = px.bar(by_dept, x='dept_name', y='promotion_count', color='promotion_count', color_continuous_scale=pal['seq'])
            fig.update_xaxes(tickangle=45)
            card("🏢 Promotions by Department (Total)", fig,
                 desc="Total promotions mapped to employees' current departments.",
                 insights=["Career‑progressive vs flat units."],
                 recs=["Create internal mobility lanes in flat units."])

        # 4 Multi‑promotion employees (Top 20)
        top_multi = promos.sort_values('promotion_count', ascending=False).head(20)
        fig = px.bar(top_multi, x='employee_id', y='promotion_count', color='promotion_count', color_continuous_scale=pal['seq'])
        card("🏅 Employees with Multiple Promotions (Top 20)", fig,
             desc="Employees with most title changes.",
             insights=["High‑trajectory talent clusters."],
             recs=["Leadership programs for high‑potentials."])

        # 5 Promotions by gender (if gender exists)
        gcol = next((c for c in ["gender","sex","Gender","Sex"] if c in snapshot.columns), None)
        if gcol:
            m = promos.merge(snapshot[['employee_id',gcol]], on='employee_id', how='left')
            by_g = m.groupby(gcol)['promotion_count'].sum().reset_index().rename(columns={gcol:'Gender'})
            fig = px.bar(by_g, x='Gender', y='promotion_count', color='promotion_count', color_continuous_scale=pal['seq'])
            card("🚻 Promotions by Gender", fig,
                 desc="Total promotions aggregated by gender.",
                 insights=["Potential bias or pipeline gaps."],
                 recs=["Calibrated panels; track ratios quarterly."])

        # 6 Career path length (title steps)
        path_len = title.groupby('employee_id').size().reset_index(name='title_steps')
        fig = px.histogram(path_len, x='title_steps', nbins=20, color_discrete_sequence=[pal['primary']])
        card("🧭 Career Path Length (Title Steps)", fig,
             desc="How many title records per employee (proxy for moves).",
             insights=["Flat paths vs dynamic careers."],
             recs=["Offer lateral moves where vertical ladders are short."])

        # 7 Promotions heatmap Dept × Year
        if 'dept_name' in snapshot.columns:
            mm = tdf[tdf['changed']==1].merge(snapshot[['employee_id','dept_name']], on='employee_id', how='left')
            heat = mm.pivot_table(index='dept_name', columns='year', values='employee_id', aggfunc='count', fill_value=0)
            fig = px.imshow(heat, aspect='auto', color_continuous_scale=pal['seq'])
            card("🔥 Promotions Heatmap (Dept × Year)", fig,
                 desc="Where/when promotions cluster.",
                 insights=["Timing and departmental cadence of promotions."],
                 recs=["Smooth cycles to reduce churn risk."])
    else:
        st.info("title.csv needs columns: employee_id, title, from_date")

# ======================= RETENTION & TURNOVER (7) ==============
with d4:
    pal = PALETTES['ret']

    # 1 Tenure distribution
    if 'company_tenure' in snapshot.columns:
        fig = px.histogram(snapshot.dropna(subset=['company_tenure']), x='company_tenure', nbins=40, color_discrete_sequence=[pal['primary']])
        card("📊 Tenure Distribution (Years)", fig,
             desc="Histogram of time in company.",
             insights=["Heavy early churn or long‑tenured core."],
             recs=["Onboarding & mentorship to reduce early exits."])

    # 2 Tenure by department
    if {'dept_name','company_tenure'}.issubset(snapshot.columns):
        fig = px.box(snapshot.dropna(subset=['dept_name','company_tenure']), x='dept_name', y='company_tenure', color='dept_name')
        fig.update_xaxes(tickangle=45, title="")
        card("📦 Tenure by Department (Box)", fig,
             desc="Spread & median tenure by department.",
             insights=["Units with systematically lower tenure."],
             recs=["Deep‑dive on workload, leadership, and growth paths."])

    # 3 Headcount over time (hires − terms if available)
    if 'hire_date' in employee.columns:
        df = employee.rename(columns={'id':'employee_id'})[['employee_id','hire_date','termination_date']] if 'termination_date' in employee.columns else employee.rename(columns={'id':'employee_id'})[['employee_id','hire_date']]
        df['hire_year'] = to_dt(df['hire_date']).dt.year
        hires = df['hire_year'].value_counts().sort_index().cumsum().reset_index(); hires.columns=['Year','Active+']
        if 'termination_date' in df.columns:
            df['term_year'] = to_dt(df['termination_date']).dt.year
            terms = df['term_year'].dropna().value_counts().sort_index().cumsum().reindex(hires['Year']).fillna(method='ffill').fillna(0).values
            hires['Active'] = hires['Active+'] - terms
        else:
            hires['Active'] = hires['Active+']
        fig = px.line(hires, x='Year', y='Active', markers=True)
        card("📉 Active Headcount Over Time", fig,
             desc="Cumulative active employees by year.",
             insights=["Growth/slowdown periods."],
             recs=["Adjust hiring plans & capacity models."])

    # 4 Turnover rate by year (if terminations exist)
    if {'hire_date','termination_date'}.issubset(employee.columns):
        e = employee.rename(columns={'id':'employee_id'}).copy()
        e['hyear'] = to_dt(e['hire_date']).dt.year
        e['tyear'] = to_dt(e['termination_date']).dt.year
        ch = e['hyear'].value_counts().sort_index().cumsum()
        ct = e['tyear'].dropna().value_counts().sort_index()
        years = sorted(set(ch.index).union(set(ct.index)))
        rate = []
        active = 0
        for y in years:
            active = ch.get(y, active) if y in ch.index else active
            term = ct.get(y, 0)
            exposure = max(active - term/2, 1)
            rate.append({"Year":y, "Turnover%": (term/exposure)*100})
        rate = pd.DataFrame(rate)
        fig = px.bar(rate, x='Year', y='Turnover%', color='Turnover%', color_continuous_scale=pal['seq'])
        card("🧾 Turnover Rate by Year (Approx)", fig,
             desc="Approximate turnover using mid‑year exposure.",
             insights=["Spikes/valleys and drivers."],
             recs=["Run exit‑theme analysis; fix top drivers."])

    # 5 Attrition by tenure band (if terminations)
    if {'termination_date','hire_date'}.issubset(employee.columns):
        e = employee.rename(columns={'id':'employee_id'})[['employee_id','hire_date','termination_date']].dropna(subset=['termination_date'])
        e['tenure_at_exit'] = (to_dt(e['termination_date']) - to_dt(e['hire_date'])).dt.days/365.25
        e['band'] = pd.cut(e['tenure_at_exit'], [0,1,2,3,5,10,50], labels=['<1y','1-2y','2-3y','3-5y','5-10y','10y+'], right=False)
        fig = px.histogram(e, x='band', color_discrete_sequence=[pal['primary']])
        card("🚪 Attrition by Tenure Band", fig,
             desc="When do exits occur along the tenure journey?",
             insights=["Early‑stage attrition vs long‑term churn."],
             recs=["Strengthen onboarding & career clarity in early months."])

    # 6 Attrition by department (if terminations)
    if {'termination_date'}.issubset(employee.columns) and 'dept_name' in snapshot.columns:
        left = employee.rename(columns={'id':'employee_id'})[['employee_id','termination_date']].dropna()
        m = left.merge(snapshot[['employee_id','dept_name']], on='employee_id', how='left').dropna()
        g = m['dept_name'].value_counts().reset_index(); g.columns=['Department','Leavers']
        fig = px.bar(g, x='Department', y='Leavers', color='Leavers', color_continuous_scale=pal['seq'])
        fig.update_xaxes(tickangle=45)
        card("🏃 Attrition by Department", fig,
             desc="Count of leavers per department.",
             insights=["Hotspots of churn."],
             recs=["Targeted engagement & manager coaching."])

    # 7 Retention by hire cohort (survival proxy)
    if 'hire_date' in employee.columns:
        e = employee.rename(columns={'id':'employee_id'})[['employee_id','hire_date','termination_date']]
        e['cohort'] = to_dt(e['hire_date']).dt.year
        e['end'] = pd.to_datetime('today')
        e['left'] = ~e['termination_date'].isna()
        # simple 1-year retention per cohort
        e['retained_1y'] = (~e['left']) | ((to_dt(e['termination_date']) - to_dt(e['hire_date'])).dt.days >= 365)
        g = e.groupby('cohort')['retained_1y'].mean().reset_index(); g['Retention%_1y'] = g['retained_1y']*100
        fig = px.bar(g, x='cohort', y='Retention%_1y', color='Retention%_1y', color_continuous_scale=pal['seq'])
        card("🛡 1‑Year Retention by Hire Cohort", fig,
             desc="Share of each hire cohort retained at least 1 year (approx).",
             insights=["Cohorts with weaker stickiness."],
             recs=["Double‑down on onboarding for weaker cohorts."])
