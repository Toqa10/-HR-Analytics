import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio
from io import BytesIO

st.set_page_config(page_title="HR Analytics Dashboard", layout="wide")

# --- Load Data ---
@st.cache_data
def load_data():
    employee = pd.read_csv("employee.csv", parse_dates=['hire_date', 'birth_date', 'termination_date'], dayfirst=True)
    salary = pd.read_csv("salary.csv", parse_dates=['from_date', 'to_date'])
    promotion = pd.read_csv("promotion.csv", parse_dates=['promotion_date'])
    return employee, salary, promotion

employee, salary, promotion = load_data()

# --- Function to download figures ---
def download_plot(fig, filename="figure.png"):
    buf = BytesIO()
    fig.write_image(buf, format="png")
    st.download_button("Download Chart", data=buf, file_name=filename, mime="image/png")

# --- Sidebar Navigation ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Demographics", "Salaries", "Promotions", "Retention"])

# --- DEMOGRAPHICS ---
if page == "Demographics":
    st.header("Employee Demographics")
    st.sidebar.markdown("## Filters for Demographics")
    show_gender_chart = st.sidebar.checkbox("Show Gender Distribution", value=True)
    show_age_chart = st.sidebar.checkbox("Show Age Distribution", value=True)

    if 'gender' in employee.columns and show_gender_chart:
        gen = employee.groupby('gender').size().reset_index(name='count')
        fig1 = px.pie(gen, names='gender', values='count', title="Gender Distribution",
                      color_discrete_sequence=px.colors.qualitative.Set2)
        st.plotly_chart(fig1, use_container_width=True)
        download_plot(fig1, "gender_distribution.png")

    if 'birth_date' in employee.columns and show_age_chart:
        employee['age'] = (pd.Timestamp.today() - employee['birth_date']).dt.days // 365
        fig2 = px.histogram(employee, x='age', nbins=30, title="Age Distribution",
                            color_discrete_sequence=[px.colors.qualitative.Pastel1[0]])
        st.plotly_chart(fig2, use_container_width=True)
        download_plot(fig2, "age_distribution.png")

# --- SALARIES ---
elif page == "Salaries":
    st.header("Salaries Analysis")
    st.sidebar.markdown("## Filters for Salaries")
    show_avg_salary = st.sidebar.checkbox("Show Average Salary per Department", value=True)
    show_salary_dist = st.sidebar.checkbox("Show Salary Distribution", value=True)

    if 'department' in salary.columns and 'salary' in salary.columns and show_avg_salary:
        avg_sal = salary.groupby('department')['salary'].mean().reset_index()
        fig3 = px.bar(avg_sal, x='department', y='salary', title="Average Salary per Department",
                      color='salary', color_continuous_scale=px.colors.sequential.Plasma)
        st.plotly_chart(fig3, use_container_width=True)
        download_plot(fig3, "avg_salary_department.png")

    if 'salary' in salary.columns and show_salary_dist:
        fig4 = px.histogram(salary, x='salary', nbins=50, title="Salary Distribution",
                            color_discrete_sequence=[px.colors.qualitative.Bold[2]])
        st.plotly_chart(fig4, use_container_width=True)
        download_plot(fig4, "salary_distribution.png")

# --- PROMOTIONS ---
elif page == "Promotions":
    st.header("Promotions Analysis")
    st.sidebar.markdown("## Filters for Promotions")
    show_promo_count = st.sidebar.checkbox("Show Promotions Count by Department", value=True)
    show_promo_trend = st.sidebar.checkbox("Show Promotions Over Time", value=True)

    # Date range filter
    if 'promotion_date' in promotion.columns:
        min_date = promotion['promotion_date'].min()
        max_date = promotion['promotion_date'].max()
        date_range = st.sidebar.date_input("Promotion Date Range", [min_date, max_date])

    promo_filtered = promotion.copy()
    if 'promotion_date' in promotion.columns:
        promo_filtered = promotion[(promotion['promotion_date'] >= pd.to_datetime(date_range[0])) &
                                   (promotion['promotion_date'] <= pd.to_datetime(date_range[1]))]

    if 'department' in promo_filtered.columns and show_promo_count:
        promo_count = promo_filtered.groupby('department').size().reset_index(name='count')
        fig5 = px.bar(promo_count, x='department', y='count', title="Promotions Count by Department",
                      color='count', color_continuous_scale=px.colors.sequential.Viridis)
        st.plotly_chart(fig5, use_container_width=True)
        download_plot(fig5, "promotions_count.png")

    if 'promotion_date' in promo_filtered.columns and show_promo_trend:
        promo_time = promo_filtered.groupby(promo_filtered['promotion_date'].dt.year).size().reset_index(name='count')
        promo_time.rename(columns={'promotion_date':'year'}, inplace=True)
        fig6 = px.line(promo_time, x='year', y='count', title="Promotions Over Time",
                       markers=True, color_discrete_sequence=[px.colors.qualitative.Set1[0]])
        st.plotly_chart(fig6, use_container_width=True)
        download_plot(fig6, "promotions_trend.png")

# --- RETENTION ---
elif page == "Retention":
    st.header("Employee Retention Analysis")
    st.sidebar.markdown("## Filters for Retention")
    show_tenure = st.sidebar.checkbox("Show Tenure Distribution", value=True)
    show_attrition_band = st.sidebar.checkbox("Show Attrition by Tenure Band", value=True)
    show_retention_1y = st.sidebar.checkbox("Show 1-Year Retention by Hire Cohort", value=True)

    e = employee.copy()

    # Optional date range for hire date
    if 'hire_date' in e.columns:
        min_hire = e['hire_date'].min()
        max_hire = e['hire_date'].max()
        hire_range = st.sidebar.date_input("Hire Date Range", [min_hire, max_hire])
        e = e[(e['hire_date'] >= pd.to_datetime(hire_range[0])) &
              (e['hire_date'] <= pd.to_datetime(hire_range[1]))]

    if show_tenure and 'hire_date' in e.columns:
        if 'termination_date' in e.columns:
            e['company_tenure'] = ((e['termination_date'].fillna(pd.Timestamp.today()) - e['hire_date']).dt.days / 365.25)
        else:
            e['company_tenure'] = (pd.Timestamp.today() - e['hire_date']).dt.days / 365.25
        fig7 = px.histogram(e, x='company_tenure', nbins=40, title="Tenure Distribution",
                            color_discrete_sequence=[px.colors.qualitative.Pastel2[3]])
        st.plotly_chart(fig7, use_container_width=True)
        download_plot(fig7, "tenure_distribution.png")

    if show_attrition_band and 'hire_date' in e.columns:
        if 'termination_date' in e.columns:
            e_left = e.dropna(subset=['termination_date']).copy()
            e_left['tenure_at_exit'] = (e_left['termination_date'] - e_left['hire_date']).dt.days / 365.25
            e_left['band'] = pd.cut(e_left['tenure_at_exit'], [0,1,2,3,5,10,50],
                                    labels=['<1y','1-2y','2-3y','3-5y','5-10y','10y+'], right=False)
            fig8 = px.histogram(e_left, x='band', title="Attrition by Tenure Band",
                                color_discrete_sequence=[px.colors.qualitative.Set3[2]])
            st.plotly_chart(fig8, use_container_width=True)
            download_plot(fig8, "attrition_tenure_band.png")

    if show_retention_1y and 'hire_date' in e.columns:
        e['cohort'] = e['hire_date'].dt.year
        if 'termination_date' in e.columns:
            e['left'] = ~e['termination_date'].isna()
            e['retained_1y'] = (~e['left']) | ((e['termination_date'] - e['hire_date']).dt.days >= 365)
        else:
            e['retained_1y'] = True
        g = e.groupby('cohort')['retained_1y'].mean().reset_index()
        g['Retention%_1y'] = g['retained_1y'] * 100
        fig9 = px.bar(g, x='cohort', y='Retention%_1y', title="1-Year Retention by Hire Cohort",
                      color='Retention%_1y', color_continuous_scale=px.colors.sequential.Aggrnyl)
        st.plotly_chart(fig9, use_container_width=True)
        download_plot(fig9, "retention_1year.png")
