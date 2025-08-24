st.sidebar.markdown("## Filters for Demographics")
show_age_dist = st.sidebar.checkbox("🎂 Age Distribution", value=True)
show_age_by_dept = st.sidebar.checkbox("🏢 Age Group by Dept", value=True)
show_headcount = st.sidebar.checkbox("👥 Headcount by Dept", value=True)
show_top_titles = st.sidebar.checkbox("🏷 Top Titles", value=True)

# الرسوم تظهر فقط لو Checkbox مفعل
if show_age_dist and 'age' in snapshot.columns:
    df = snapshot.dropna(subset=['age'])
    fig = px.histogram(df, x='age', nbins=40, color_discrete_sequence=[pal['primary']])
    card("🎂 Age Distribution", fig)

if show_age_by_dept and {'age','dept_name'}.issubset(snapshot.columns):
    tmp = snapshot.copy()
    tmp['age_group'] = pd.cut(tmp['age'], [10,20,30,40,50,60,70],
                              labels=['10s','20s','30s','40s','50s','60s'], right=False)
    pivot = tmp.pivot_table(index='dept_name', columns='age_group', values='employee_id', aggfunc='count', fill_value=0).reset_index()
    fig = px.bar(pivot, x='dept_name', y=pivot.columns[1:], barmode='stack', color_discrete_sequence=pal['seq'])
    fig.update_xaxes(tickangle=45)
    card("🏢 Age Group Composition by Department", fig)

if show_headcount and 'dept_name' in snapshot.columns:
    dep = snapshot['dept_name'].value_counts().reset_index()
    dep.columns = ['Department','Headcount']
    fig = px.bar(dep, x='Department', y='Headcount', color='Headcount', color_continuous_scale=pal['seq'])
    card("👥 Headcount by Department", fig)

if show_top_titles and 'title' in snapshot.columns:
    t = snapshot['title'].fillna('Unknown').value_counts().head(20).reset_index()
    t.columns = ['Title','Headcount']
    fig = px.bar(t, x='Title', y='Headcount', color='Headcount', color_continuous_scale=pal['seq'])
    fig.update_xaxes(tickangle=45)
    card("🏷 Top Titles", fig)
