# ============================ DEMOGRAPHICS =======================
if page == "Demographics":
    pal = PALETTES['demo']
    df = snapshot.dropna(subset=['age'])
    
    # 1. Age Distribution
    fig1 = px.histogram(df, x='age', nbins=40, color_discrete_sequence=[pal['primary']])
    card("🎂 Age Distribution", fig1)

    # 2. Age by Dept
    if {'age','dept_name'}.issubset(snapshot.columns):
        tmp = snapshot.copy()
        tmp['age_group'] = pd.cut(tmp['age'], [10,20,30,40,50,60,70], labels=['10s','20s','30s','40s','50s','60s'], right=False)
        pivot = tmp.pivot_table(index='dept_name', columns='age_group', values='employee_id', aggfunc='count', fill_value=0).reset_index()
        fig2 = px.bar(pivot, x='dept_name', y=pivot.columns[1:], barmode='stack', color_discrete_sequence=pal['seq'])
        fig2.update_xaxes(tickangle=45)
        card("🏢 Age Group by Department", fig2)

    # 3. Headcount by Dept
    hc = snapshot.groupby("dept_name").size().reset_index(name="headcount")
    fig3 = px.bar(hc, x="dept_name", y="headcount", color_discrete_sequence=[pal['accent']])
    fig3.update_xaxes(tickangle=45)
    card("👥 Headcount by Department", fig3)

    # 4. Top Titles
    top_titles = snapshot['title'].value_counts().reset_index().rename(columns={'index':'title','title':'count'}).head(10)
    fig4 = px.bar(top_titles, x='title', y='count', color_discrete_sequence=[pal['primary']])
    fig4.update_xaxes(tickangle=45)
    card("🏆 Top Titles", fig4)

    # 5. Age by Dept (Box)
    fig5 = px.box(snapshot, x='dept_name', y='age', color_discrete_sequence=[pal['accent']])
    fig5.update_xaxes(tickangle=45)
    card("📦 Age Distribution by Department (Boxplot)", fig5)

    # 6. Gender Mix
    gen_mix = snapshot['gender'].value_counts().reset_index().rename(columns={'index':'gender','gender':'count'})
    fig6 = px.pie(gen_mix, names='gender', values='count', color_discrete_sequence=pal['seq'])
    card("⚥ Gender Mix", fig6)

    # 7. Gender by Dept
    gen_dept = snapshot.groupby(['dept_name','gender']).size().reset_index(name='count')
    fig7 = px.bar(gen_dept, x='dept_name', y='count', color='gender', barmode='stack', color_discrete_sequence=pal['seq'])
    fig7.update_xaxes(tickangle=45)
    card("⚥ Gender Distribution by Department", fig7)

    # 8. Age x Tenure Heatmap
    heat = snapshot.pivot_table(index=pd.cut(snapshot['age'], bins=10), 
                                columns=pd.cut(snapshot['company_tenure'], bins=10), 
                                values='employee_id', aggfunc='count', fill_value=0)
    fig8 = px.imshow(heat, text_auto=True, color_continuous_scale=pal['seq'])
    card("🌡 Age x Tenure Heatmap", fig8)
