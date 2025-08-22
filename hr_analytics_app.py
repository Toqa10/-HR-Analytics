import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 💠 ألوان
pink = "#ff69b4"
black = "#000000"

# 🧠 تحميل البيانات
@st.cache_data
def load_data():
    # تأكد إن كل الملفات CSV و موجودة في نفس المجلد
    salary = pd.read_csv("salary.csv")
    employee = pd.read_csv("employee.csv")
    current_emp_snapshot = pd.read_csv("current_employee_snapshot.csv")
    department = pd.read_csv("department.csv")
    department_employee = pd.read_csv("department_employee.csv")
    department_manager = pd.read_csv("department_manager.csv")
    title = pd.read_csv("title.csv")

    # حساب العمر
    emp_snapshot = current_emp_snapshot.merge(employee, left_on="employee_id", right_on="id", how="left")
    emp_snapshot["birth_date"] = pd.to_datetime(emp_snapshot["birth_date"])
    emp_snapshot["age"] = datetime.now().year - emp_snapshot["birth_date"].dt.year
    emp_snapshot.dropna(subset=["salary_amount"], inplace=True)

    return salary, employee, emp_snapshot, department_employee, department, department_manager, title

# 🗂️ تحميل كل البيانات
salary, employee, current_emp_snapshot, department_employee, department, department_manager, title = load_data()

# 🧩 تأمين الأعمدة المفقودة مؤقتًا
for col in ['age', 'title', 'dept_name', 'company_tenure', 'moved_department']:
    if col not in employee.columns:
        employee[col] = np.nan

emp_snapshot = current_emp_snapshot.copy()

# 💻 واجهة Streamlit
st.markdown(f"<h1 style='color:{pink}; text-align:center;'> HR Analytics Dashboard</h1>", unsafe_allow_html=True)
st.markdown("---")

# خيارات المستخدم
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
    "common titles by age group"
]

question = st.selectbox("Choose a business insight:", options)
center_button = st.button("✨ Show me the Insight ✨")

if center_button and question:
    question = question.strip().lower()
    fig = None

    if question == "top salaries":
        top = salary.groupby('employee_id')['amount'].max().sort_values(ascending=False).head(10).reset_index()
        top.columns = ['Employee ID', 'Top Salary']
        st.markdown("### 💰 Top 10 Salaries (Table View)")
        st.dataframe(top.style.format({'Top Salary': '{:,.0f}'}), use_container_width=True)

    elif question == "average salary per year":
        salary['from_date'] = pd.to_datetime(salary['from_date'])
        salary['year'] = salary['from_date'].dt.year
        avg_salary_per_year = salary.groupby('year')['amount'].mean().reset_index()
        fig = px.line(avg_salary_per_year, x='year', y='amount', title="Average Salary Over Time", markers=True)
        fig.update_traces(line=dict(color='deeppink', width=3))
        fig.update_layout(template='plotly_dark', plot_bgcolor='black', paper_bgcolor='black', font=dict(color=pink))

    elif question == "salary growth":
        emp_growth = salary.groupby('employee_id')['amount'].agg(['min', 'max'])
        emp_growth['growth_%'] = ((emp_growth['max'] - emp_growth['min']) / emp_growth['min']) * 100
        top_growth = emp_growth.sort_values(by='growth_%', ascending=False).head(10).reset_index()
        fig = px.bar(top_growth, x='employee_id', y='growth_%', title="Top 10 Salary Growth %", color='growth_%', color_continuous_scale='RdPu')

    elif question == "distribution of employee ages":
        age_counts = current_emp_snapshot['age'].value_counts().sort_index().reset_index()
        age_counts.columns = ['Age', 'Count']
        fig = px.bar(age_counts, x='Count', y='Age', orientation='h', title='🎂 Distribution of Employee Ages', color='Count', color_continuous_scale=px.colors.sequential.Pinkyl)
        fig.update_traces(text=age_counts['Count'], textposition='outside')
        fig.update_layout(template='plotly_dark', plot_bgcolor='black', paper_bgcolor='black')

    elif question == "department with highest average salary":
        merged = current_emp_snapshot[['employee_id', 'dept_name']].merge(salary, on='employee_id')
        dept_avg = merged.groupby('dept_name')['amount'].mean().reset_index().sort_values(by='amount', ascending=False)
        fig = px.bar(dept_avg, x='dept_name', y='amount', title="Avg Salary per Department", color='amount', color_continuous_scale='pinkyl')

    elif question == "tenure vs salary by department":
        merged = current_emp_snapshot.merge(salary, on="employee_id")
        fig = px.scatter(merged, x='company_tenure', y='amount', facet_col='dept_name', facet_col_wrap=3, color='dept_name', title='⏳ Tenure vs Salary by Department 💼', hover_data=['employee_id'])
        fig.update_layout(template='plotly_dark', plot_bgcolor='black', paper_bgcolor='black', height=800)

    elif question == "salary distribution by department":
        merged = current_emp_snapshot.merge(salary, on="employee_id")
        fig = px.scatter(merged, x="dept_name", y="amount", color="dept_name", title="💸 Salary Distribution by Department", hover_data=["employee_id"])
        fig.update_layout(template="plotly_dark", plot_bgcolor="black", paper_bgcolor="black")

    elif question == "employee distribution":
        dept_dist = current_emp_snapshot['dept_name'].value_counts().reset_index()
        dept_dist.columns = ['Department', 'Count']
        fig = px.bar(dept_dist, x='Department', y='Count', title="Employee Distribution by Department", color='Count', color_continuous_scale='Agsunset')

    elif question == "common titles by age group":
        current_emp_snapshot["age_group"] = pd.cut(current_emp_snapshot["age"], bins=[10,20,30,40,50,60,70], labels=['10s','20s','30s','40s','50s','60s'], right=False)
        def most_common_title(x): return x.value_counts().idxmax() if len(x)>0 else None
        top_titles_by_group = current_emp_snapshot.groupby("age_group")["title"].agg(most_common_title).reset_index()
        top_titles_by_group.columns = ['Age Group', 'Most Common Title']
        title_counts = current_emp_snapshot.pivot_table(index='title', columns='age_group', values='employee_id', aggfunc='count', fill_value=0)
        top_titles = current_emp_snapshot['title'].value_counts().head(5).index
        title_counts_top = title_counts.loc[title_counts.index.isin(top_titles)]
        fig = go.Figure()
        for title in title_counts_top.index:
            fig.add_trace(go.Scatterpolar(r=title_counts_top.loc[title].values, theta=title_counts_top.columns.astype(str), fill='toself', name=title))
        fig.update_layout(title='🕸 Most Common Titles by Age Group (Spider Chart)', polar=dict(bgcolor='black', radialaxis=dict(visible=True, color=pink)), template='plotly_dark')

    elif question == "average salary per job title":
        merged = current_emp_snapshot.merge(salary, on="employee_id")
        avg_salary_per_title = merged.groupby("title")["amount"].mean().sort_values(ascending=False).reset_index()
        fig = px.scatter(merged, x="title", y="amount", color="title", size="amount", title="💼 Average Salary per Job Title (Scatter)")
        fig.update_layout(template="plotly_dark", plot_bgcolor="black", paper_bgcolor="black")

    else:
        st.warning("⚠️ Please enter a valid question.")

    if fig:
        st.plotly_chart(fig, use_container_width=True)

