import streamlit as st
import pandas as pd
import plotly.express as px

# --------------------------
# LOAD DATA
# --------------------------
st.set_page_config(layout="wide")

st.title("📊 ECE Department Publications Dashboard")

# Upload Excel
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # --------------------------
    # CLEAN DATA (IMPORTANT)
    # --------------------------
    df.columns = df.columns.str.strip()

    # --------------------------
    # SIDEBAR FILTERS
    # --------------------------
    st.sidebar.header("Filters")

    category = st.sidebar.multiselect(
        "Category",
        options=df["category"].dropna().unique()
    )

    year = st.sidebar.multiselect(
        "Year",
        options=df["year"].dropna().unique()
    )

    faculty = st.sidebar.multiselect(
        "Faculty",
        options=df["faculty"].dropna().unique()
    )

    status = st.sidebar.multiselect(
        "Status",
        options=df["status"].dropna().unique()
    )

    # Apply filters
    filtered_df = df.copy()

    if category:
        filtered_df = filtered_df[filtered_df["category"].isin(category)]

    if year:
        filtered_df = filtered_df[filtered_df["year"].isin(year)]

    if faculty:
        filtered_df = filtered_df[filtered_df["faculty"].isin(faculty)]

    if status:
        filtered_df = filtered_df[filtered_df["status"].isin(status)]

    # --------------------------
    # METRICS
    # --------------------------
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Papers", len(filtered_df))
    col2.metric("Journals", len(filtered_df[filtered_df["category"] == "Journal"]))
    col3.metric("Conferences", len(filtered_df[filtered_df["category"] == "Conference"]))
    col4.metric("Faculty", filtered_df["faculty"].nunique())

    # --------------------------
    # CHARTS
    # --------------------------

    st.subheader("📈 Publications by Year")
    year_chart = filtered_df.groupby("year").size().reset_index(name="count")
    fig1 = px.bar(year_chart, x="year", y="count")
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("📊 Category Distribution")
    cat_chart = filtered_df["category"].value_counts().reset_index()
    cat_chart.columns = ["category", "count"]
    fig2 = px.pie(cat_chart, names="category", values="count")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("📊 Quartile Distribution")
    if "quartile" in df.columns:
        q_chart = filtered_df["quartile"].value_counts().reset_index()
        q_chart.columns = ["quartile", "count"]
        fig3 = px.bar(q_chart, x="quartile", y="count")
        st.plotly_chart(fig3, use_container_width=True)

    st.subheader("👨‍🏫 Publications by Faculty")
    fac_chart = filtered_df["faculty"].value_counts().reset_index()
    fac_chart.columns = ["faculty", "count"]
    fig4 = px.bar(fac_chart, x="faculty", y="count")
    st.plotly_chart(fig4, use_container_width=True)

    # --------------------------
    # TABLE
    # --------------------------
    st.subheader("📋 All Publications")

    search = st.text_input("Search")

    if search:
        filtered_df = filtered_df[
            filtered_df.apply(lambda row: search.lower() in str(row).lower(), axis=1)
        ]

    st.dataframe(filtered_df, use_container_width=True)

else:
    st.info("Please upload your Excel file to see dashboard.")
