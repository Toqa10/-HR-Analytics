# hr_dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px

# ===============================================
# Helper Functions
# ===============================================
def has_cols(df, cols):
    return all(col in df.columns for col in cols)

def card(title, fig, desc="", insights=[], recs=[]):
    st.subheader(title)
    st.plotly_chart(fig, use_container_width=True)
    if desc:
        st.markdown(f"**Description:** {desc}")
    if insights:
        st.markdown("**Insights:**")
        for i in insights:
            st.markdown(f"- {i}")
    if recs:
        st.markdown("**Recommendations:**")
        for r in recs:
            st.markdown(f"- {r}")
    st.markdown("---")

# ===============================================
# Palette
# ===============================================
PALETTES = {
    'demo': {'primary':'#636EFA','accent':'#EF553B'},
    'pay': {'primary':'#00CC96','accent':'#AB63FA'},
    'promo': {'primary':'#FFA15A','accent':'#19D3F3'},
    'ret': {'primary':'#FF6692','accent':'#B6E880'}
}

# ===============================================
# Load Data
# ===============================================
st.title("📊 HR Analytics Dashboard")
st.markdown("Visual insights into your HR data.")

uploaded_file = st.file_uploader("Upload your HR CSV snapshot", type="csv")
if uploaded_file:
    snapshot = pd.read_csv(uploaded_file)

    # Sidebar navigation
    page = st.sidebar.selectbox(
        "Select HR Section",
        ["👤 Demographics", "💵 Salaries & Compensation",
         "🚀 Promotions & Career Growth", "🧲 Retention & Turnover"]
    )

    # ===============================================
    # 1. Demographics
    # ===============================================
    if page == "👤 Demographics":
        pal = PALETTES['demo']

        if 'age' in snapshot.columns:
            df = snapshot.dropna(subset=['age'])
            if not df.empty:
                fig = px.histogram(df, x='age', nbins=40, color_discrete_sequence=[pal['primary']])
                card(
                    "🎂 Age Distribution", fig,
                    desc="Histogram of employees' ages.",
                    insights=["Dominant age bands and outliers."],
                    recs=["Tailor L&D and benefits by age clusters."]
                )

        if 'gender' in snapshot.columns:
            df = snapshot['gender'].value_counts().reset_index()
            df.columns = ['gender','count']
            fig = px.pie(df, values='count', names='gender', color_discrete_sequence=px.colors.sequential.Blues)
            card(
                "⚥ Gender Distribution", fig,
                desc="Percentage of male vs female employees.",
                insights=["Identify gender balance or imbalance."],
                recs=["Consider diversity initiatives if imbalance exists."]
            )

        if 'dept_name' in snapshot.columns:
            df = snapshot['dept_name'].value_counts().reset_index()
            df.columns = ['Department','Count']
            fig = px.bar(df, x='Department', y='Count', color='Count', color_continuous_scale=px.colors.sequential.Blues)
            card(
                "🏢 Department Distribution", fig,
                desc="Number of employees per department.",
                insights=["Shows staffing levels and potential bottlenecks."],
                recs=["Review hiring needs per department."]
            )

    # ===============================================
    # 2. Salaries & Compensation
    # ===============================================
    elif page == "💵 Salaries & Compensation":
        pal = PALETTES['pay']

        if 'latest_salary' in snapshot.columns:
            df = snapshot.dropna(subset=['latest_salary'])
            fig = px.histogram(df, x='latest_salary', nbins=50, color_discrete_sequence=[pal['primary']])
            card(
                "💰 Salary Distribution", fig,
                desc="Distribution of current salaries.",
                insights=["Identify clusters, outliers, and ranges."],
                recs=["Review pay parity and adjust compensation bands if needed."]
            )

        if has_cols(snapshot, ['dept_name','latest_salary']):
            df = snapshot.groupby('dept_name')['latest_salary'].median().reset_index()
            fig = px.bar(df, x='dept_name', y='latest_salary', color='latest_salary', color_continuous_scale=px.colors.sequential.Greens)
            card(
                "🏢 Median Salary by Department", fig,
                desc="Median salary per department.",
                insights=["Highlights which departments have higher/lower pay."],
                recs=["Adjust budgets or compensation strategy by department."]
            )

        if has_cols(snapshot, ['company_tenure','latest_salary']):
            df = snapshot.dropna(subset=['company_tenure','latest_salary'])
            fig = px.scatter(df, x='company_tenure', y='latest_salary', color_discrete_sequence=[pal['accent']])
            card(
                "⏱ Salary vs Tenure", fig,
                desc="Scatter plot of salary vs years in company.",
                insights=["Shows pay progression with tenure."],
                recs=["Review promotion and raise policies."]
            )

    # ===============================================
    # 3. Promotions & Career Growth
    # ===============================================
    elif page == "🚀 Promotions & Career Growth":
        pal = PALETTES['promo']

        if 'title' in snapshot.columns:
            df = snapshot['title'].value_counts().reset_index()
            df.columns = ['Title','Count']
            fig = px.bar(df, x='Title', y='Count', color='Count', color_continuous_scale=px.colors.sequential.Purples)
            card(
                "🏷 Job Title Distribution", fig,
                desc="Distribution of current job titles.",
                insights=["Shows how employees are spread across positions."],
                recs=["Identify roles with promotion opportunities."]
            )

        if has_cols(snapshot, ['employee_id','title']):
            promotions = snapshot.sort_values(['employee_id','title']).groupby('employee_id').size().reset_index(name='promotions')
            fig = px.histogram(promotions, x='promotions', nbins=10, color_discrete_sequence=[pal['primary']])
            card(
                "📈 Promotions Count per Employee", fig,
                desc="Number of promotions each employee received.",
                insights=["Highlights growth paths."],
                recs=["Identify employees with low promotion frequency for engagement planning."]
            )

        if has_cols(snapshot, ['title','company_tenure']):
            df = snapshot.groupby('title')['company_tenure'].mean().reset_index()
            fig = px.bar(df, x='title', y='company_tenure', color='company_tenure', color_continuous_scale=px.colors.sequential.Purples)
            card(
                "⏳ Average Tenure per Title", fig,
                desc="Average years employees spend per title.",
                insights=["Shows time needed before promotion."],
                recs=["Use for career path planning and L&D focus."]
            )

    # ===============================================
    # 4. Retention & Turnover
    # ===============================================
    elif page == "🧲 Retention & Turnover":
        pal = PALETTES['ret']

        if 'termination_date' in snapshot.columns:
            df = snapshot['termination_date'].dropna()
            fig = px.histogram(df, x='termination_date', nbins=50, color_discrete_sequence=[pal['primary']])
            card(
                "❌ Terminations Over Time", fig,
                desc="Histogram of employee terminations.",
                insights=["Shows spikes in turnover."],
                recs=["Investigate causes during peak periods."]
            )

        if has_cols(snapshot, ['dept_name','termination_date']):
            df = snapshot[snapshot['termination_date'].notna()]
            df = df['dept_name'].value_counts().reset_index()
            df.columns = ['Department','Terminations']
            fig = px.bar(df, x='Department', y='Terminations', color='Terminations', color_continuous_scale=px.colors.sequential.OrRd)
            card(
                "🏢 Department Turnover", fig,
                desc="Terminations by department.",
                insights=["Departments with high turnover are highlighted."],
                recs=["Target retention programs in these departments."]
            )

        if has_cols(snapshot, ['company_tenure','termination_date']):
            df = snapshot[snapshot['termination_date'].notna()]
            fig = px.histogram(df, x='company_tenure', nbins=40, color_discrete_sequence=[pal['accent']])
            card(
                "⏱ Tenure at Exit", fig,
                desc="Tenure distribution of employees who left.",
                insights=["Identifies typical retention period."],
                recs=["Enhance retention strategies at critical tenure periods."]
            )

else:
    st.info("Upload a CSV file to display HR Analytics Dashboard.")
