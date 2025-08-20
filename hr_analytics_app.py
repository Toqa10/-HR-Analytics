import streamlit as st
import pandas as pd
import numpy as np
import matplotlib
import requests
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from datetime import datetime
from plotly.subplots import make_subplots



# 💠 ألوان
pink = "#ff69b4"
black = "#000000"

# 🧠 تحميل البيانات
@st.cache_data
def load_data():
    salary_url = "https://drive.google.com/uc?export=download&id=1MtK2OqbwVfSr0mqWQK9na0jFMZnjG93d"
    salary = pd.read_csv(salary_url)

    employee = pd.read_csv("employee.csv", encoding='utf-8')
    current_emp_snapshot = pd.read_csv("current_employee_snapshot.csv", encoding='utf-8')
    department = pd.read_csv("department.csv", encoding='utf-8') 
    department_employee = pd.read_csv("department_employee.csv", encoding='utf-8')
    department_manager = pd.read_csv("department_manager.csv", encoding='utf-8')
    title = pd.read_csv("title.csv", encoding='utf-8')

    # حساب العمر
    emp_snapshot = current_emp_snapshot.merge(employee, left_on="employee_id", right_on="id", how="left")
    emp_snapshot["birth_date"] = pd.to_datetime(emp_snapshot["birth_date"])
    emp_snapshot["age"] = datetime(2002, 12, 12).year - emp_snapshot["birth_date"].dt.year
    emp_snapshot.dropna(subset=["salary_amount"], inplace=True)

    return salary, employee, emp_snapshot, department_employee, department, department_manager, title




# 🗂️ تحميل كل البيانات
salary, employee, current_emp_snapshot, department_employee, department, department_manager, title = load_data()

# 🧩 تأمين الأعمدة المفقودة (مؤقتًا)
for col in ['age', 'title', 'dept_name', 'company_tenure', 'moved_department']:
    if col not in employee.columns:
        employee[col] = np.nan

emp_snapshot = current_emp_snapshot.copy()

# تخصيص CSS للتصميم
import streamlit as st

import streamlit as st

st.markdown("""
<style>
/* الخلفية */
[data-testid="stAppViewContainer"] {
    background-color: black;
    position: fixed;
    overflow: hidden;
}

/* إعدادات النجوم */
.star {
    position: fixed;
    border-radius: 50%;
    animation: blink 2s infinite ease-in-out;
    opacity: 0.8;
    z-index: 0;
    pointer-events: none;
}

/* تأثير الوميض */
@keyframes blink {
    0%, 100% { opacity: 0.2; }
    50% { opacity: 1; }
}

/* كل نجمة بلون ومكان مختلف */
.star1 { top: 10%; left: 20%; width: 2px; height: 2px; background-color: #ff69b4; animation-delay: 0s; }
.star2 { top: 20%; left: 70%; width: 3px; height: 3px; background-color: #ba55d3; animation-delay: 0.4s; }
.star3 { top: 30%; left: 40%; width: 1.5px; height: 1.5px; background-color: #dda0dd; animation-delay: 1s; }
.star4 { top: 50%; left: 60%; width: 2.5px; height: 2.5px; background-color: #ff1493; animation-delay: 0.2s; }
.star5 { top: 70%; left: 25%; width: 1.8px; height: 1.8px; background-color: #db7093; animation-delay: 1.4s; }
.star6 { top: 80%; left: 85%; width: 1.3px; height: 1.3px; background-color: #d8bfd8; animation-delay: 0.8s; }
.star7 { top: 15%; left: 90%; width: 2.2px; height: 2.2px; background-color: #c71585; animation-delay: 0.6s; }
.star8 { top: 65%; left: 10%; width: 2.1px; height: 2.1px; background-color: #ffb6c1; animation-delay: 1.2s; }

/* تنسيق النصوص */
h1, .stSelectbox label, .stButton button {
    color: #ffffff;
    font-family: 'Segoe UI', sans-serif;
    font-size: 28px;
}

/* تنسيق selectbox */
.stSelectbox>div>div {
    font-size: 22px;
}

/* زرار Streamlit */
.stButton button {
    border: 2px solid #ff69b4;
    background-color: #222222;
    color: #ffffff;
    border-radius: 30px;
    font-size: 24px;
    font-family: 'Segoe UI', sans-serif;
    padding: 20px 50px;
    margin-top: -10px;
    transition: all 0.3s ease-in-out;
}

/* تأثير hover */
.stButton button:hover {
    background-color: #ff69b4;
    color: #000000;
    transform: scale(1.08);
    box-shadow: 0 0 15px #ff69b4;
}

/* تكبير الشارت عند الظهور */
.element-container .stPlotlyChart {
    transform: scale(1.05);
    transition: transform 0.5s ease-in-out;
}
</style>

<!-- نجوم -->
<div class="star star1"></div>
<div class="star star2"></div>
<div class="star star3"></div>
<div class="star star4"></div>
<div class="star star5"></div>
<div class="star star6"></div>
<div class="star star7"></div>
<div class="star star8"></div>
""", unsafe_allow_html=True)

st.markdown(f"<h1 style='color:{pink}; text-align:center;'>💼 HR Analytics Dashboard</h1>", unsafe_allow_html=True)
st.markdown("---")

# إدخال المستخدم وزرار التفاعل
options = [
    "top salaries",
    "average salary per year",
    "salary growth",
    "Distribution of Employee Ages",
    "department with highest average salary",
    "Distribution of Tenure Years per Department",
    "Tenure vs Salary by Department",
    "Salary Distribution by Department",
    "employee distribution",
    "Average Salary per Job Title",
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

      # استخدام تدرج لوني وردي غامق
       st.dataframe(
          top.style
          .format({'Top Salary': '{:,.0f}'})
          .background_gradient(cmap='pink'), 
           use_container_width=True
        )

    elif question == "average salary per year":
        salary['from_date'] = pd.to_datetime(salary['from_date'])
        salary['year'] = salary['from_date'].dt.year
        avg_salary_per_year = salary.groupby('year')['amount'].mean().reset_index()
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=avg_salary_per_year['year'],
            y=avg_salary_per_year['amount'],
            mode='lines+markers',
            line=dict(color='deeppink', width=3),
            marker=dict(size=8, color='black', line=dict(width=2, color='deeppink')),
            name='Average Salary'
        ))
        fig.update_layout(
            title='Average Salary Over Time',
            xaxis_title='Year',
            yaxis_title='Average Salary',
            template='plotly_dark',
            plot_bgcolor='black',
            paper_bgcolor='black',
            font=dict(family='Arial', color='pink', size=14),
            title_font=dict(size=22, color='pink')
        )

    elif question == "salary growth":
        emp_growth = salary.groupby('employee_id')['amount'].agg(['min', 'max'])
        emp_growth['growth_%'] = ((emp_growth['max'] - emp_growth['min']) / emp_growth['min']) * 100
        top_growth = emp_growth.sort_values(by='growth_%', ascending=False).head(10).reset_index()
        fig = px.bar(top_growth, x='employee_id', y='growth_%', title="Top 10 Salary Growth %", color='growth_%', color_continuous_scale='RdPu')

    elif question == "distribution of employee ages":
        age_counts = current_emp_snapshot['age'].value_counts().sort_index().reset_index()
        age_counts.columns = ['Age', 'Count']
        fig = px.bar(
            age_counts,
            x='Count',
            y='Age',
            orientation='h',
            title='🎂 Distribution of Employee Ages',
            color='Count',
            color_continuous_scale=px.colors.sequential.Pinkyl,
            text='Count'
        )
        fig.update_layout(
            template='plotly_dark',
            plot_bgcolor='black',
            paper_bgcolor='black',
            font=dict(family='Arial', color='pink', size=14),
            title_font=dict(size=24, color='pink'),
            xaxis_title='Number of Employees',
            yaxis_title='Age',
            bargap=0.3
        )
        fig.update_traces(textposition='outside')

    elif question == "department with highest average salary":
        merged = current_emp_snapshot[['employee_id', 'dept_name']].merge(salary, on='employee_id')
        dept_avg = merged.groupby('dept_name')['amount'].mean().reset_index().sort_values(by='amount', ascending=False)
        fig = px.bar(dept_avg, x='dept_name', y='amount', title="Avg Salary per Department", color='amount', color_continuous_scale='pinkyl')


    elif question == "tenure vs salary by department":
        merged = current_emp_snapshot.merge(salary, on="employee_id")
        fig = px.scatter(
            merged,
            x='company_tenure',
            y='amount',
            facet_col='dept_name',
            facet_col_wrap=3,
            color='dept_name',
            title='⏳ Tenure vs Salary by Department 💼',
            color_discrete_sequence=px.colors.sequential.Pinkyl,
            hover_data=['employee_id']
        )
        fig.update_layout(
            template='plotly_dark',
            plot_bgcolor='black',
            paper_bgcolor='black',
            font=dict(family='Arial', color='pink', size=14),
            title_font=dict(size=22, color='pink'),
            height=800,
            margin=dict(t=100)
        )
        fig.update_xaxes(title='Tenure (Years)')
        fig.update_yaxes(title='Salary')

    elif question == "salary distribution by department":
        merged = current_emp_snapshot.merge(salary, on="employee_id")
        fig = px.scatter(
            merged,
            x="dept_name",
            y="amount",
            color="dept_name",
            title="💸 Salary Distribution by Department",
            color_discrete_sequence=px.colors.sequential.Pinkyl,
            hover_data=["employee_id"]
        )
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor="black",
            paper_bgcolor="black",
            font=dict(family="Arial", color="pink", size=14),
            title_font=dict(size=22, color="pink"),
            xaxis_title="Department",
            yaxis_title="Salary Amount"
        )

    elif question == "distribution of employees by title":
        merged = current_emp_snapshot.merge(salary, on="employee_id")
        title_counts = merged["title"].value_counts().reset_index()
        title_counts.columns = ["title", "count"]
        fig = px.bar(
            title_counts,
            x="title",
            y="count",
            title="👩‍💼 Distribution of Employees by Title",
            color="count",
            color_continuous_scale=px.colors.sequential.Pinkyl,
            text_auto=True
        )
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor="black",
            paper_bgcolor="black",
            font=dict(family="Arial", color="pink", size=14),
            title_font=dict(size=22, color="pink"),
            xaxis_title="Job Title",
            yaxis_title="Number of Employees",
            xaxis_tickangle=45
        )

    elif question == "employee distribution":
        dept_dist = current_emp_snapshot['dept_name'].value_counts().reset_index()
        dept_dist.columns = ['Department', 'Count']
        fig = px.bar(dept_dist, x='Department', y='Count', title="Employee Distribution by Department", color='Count', color_continuous_scale='Agsunset')

    elif question == "common titles by age group":
        if "age_group" not in current_emp_snapshot.columns:
            current_emp_snapshot["age_group"] = pd.cut(
                current_emp_snapshot["age"],
                bins=[10, 20, 30, 40, 50, 60, 70],
                labels=['10s', '20s', '30s', '40s', '50s', '60s'],
                right=False
            )
        def most_common_title(x):
            if len(x) == 0:
                return None
            return x.value_counts().idxmax()
        top_titles_by_group = current_emp_snapshot.groupby("age_group")["title"].agg(most_common_title).reset_index()
        top_titles_by_group.columns = ['Age Group', 'Most Common Title']
        top_titles_by_group = top_titles_by_group.dropna(subset=['Most Common Title'])
        title_counts = current_emp_snapshot.pivot_table(
            index='title',
            columns='age_group',
            values='employee_id',
            aggfunc='count',
            fill_value=0
        )
        top_titles = current_emp_snapshot['title'].value_counts().head(5).index
        title_counts_top = title_counts.loc[title_counts.index.isin(top_titles)]
        fig = go.Figure()
        for title in title_counts_top.index:
            fig.add_trace(go.Scatterpolar(
                r=title_counts_top.loc[title].values,
                theta=title_counts_top.columns.astype(str),
                fill='toself',
                name=title
            ))
        fig.update_layout(
            title='🕸 Most Common Titles by Age Group (Spider Chart)',
            polar=dict(
                bgcolor='black',
                radialaxis=dict(visible=True, color='pink', gridcolor='deeppink'),
                angularaxis=dict(color='pink')
            ),
            showlegend=True,
            template='plotly_dark',
            paper_bgcolor='black',
            font=dict(family='Arial', color='pink', size=13),
            title_font=dict(size=22, color='pink')
        )

    elif question == "average salary per job title":
        
        merged = current_emp_snapshot.merge(salary, on="employee_id")
        avg_salary_per_title = merged.groupby("title")["amount"].mean().sort_values(ascending=False).reset_index()
        fig = px.scatter(
         merged,
         x="title",
         y="amount",
         color="title",
         size="amount",
         title="💼 Average Salary per Job Title (Scatter)",
         color_discrete_sequence=px.colors.sequential.Pinkyl
        )
        fig.update_layout(
            template="plotly_dark",
            plot_bgcolor="black",
            paper_bgcolor="black",
            font=dict(family="Arial", color="pink", size=14),
            title_font=dict(size=22, color="pink"),
            xaxis_title="Job Title",
            yaxis_title="Average Salary"
        )
    


    else:
        st.warning("⚠️ Please enter a valid question.")

    # Show figure only if it exists
    if hasattr(fig, 'update_layout'):  # أو ممكن isinstance(fig, (go.Figure, px.Figure)) لو عايزة توسعي أكتر
      fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="black",
        paper_bgcolor="black",
        font=dict(family="Arial", color="pink", size=14),
        title_font=dict(size=22, color="pink")
    )
    st.plotly_chart(fig, use_container_width=True)
st.markdown(f"<p style='color:{pink}; font-size:12px; text-align:center;'>Made with ❤️ by Mayar</p>", unsafe_allow_html=True)
