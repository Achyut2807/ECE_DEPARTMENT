import streamlit as st
import pandas as pd
import plotly.express as px

# --------------------------
# PAGE SETUP
# --------------------------
st.set_page_config(layout="wide")
st.title("📊 ECE Department Publications Dashboard")

# --------------------------
# FILE UPLOAD
# --------------------------
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if uploaded_file:

    # --------------------------
    # LOAD DATA (CORRECT HEADER)
    # --------------------------
    df = pd.read_excel(uploaded_file, header=0)

    # --------------------------
    # CLEAN COLUMN NAMES
    # --------------------------
    df.columns = df.columns.str.strip().str.lower()

    st.write("Detected Columns:", df.columns.tolist())

    # --------------------------
    # RENAME BASED ON YOUR FILE
    # --------------------------
    df = df.rename(columns={
        "publication year": "year",
        "publication category": "category",
        "publication title": "title",
        "name of authors as mentioned in publication": "faculty",
        "status": "status",
        "quartile": "quartile"
    })

    # --------------------------
    # FIX YEAR COLUMN (IMPORTANT)
    # --------------------------
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["year"])
    df["year"] = df["year"].astype(int)

    # --------------------------
    # REMOVE EMPTY ROWS
    # --------------------------
    df = df.dropna(subset=["title"])

    # --------------------------
    # SIDEBAR FILTERS
    # --------------------------
    st.sidebar.header("🔍 Filters")

    category = st.sidebar.multiselect(
        "Category",
        df["category"].dropna().unique()
    )

    year = st.sidebar.multiselect(
        "Year",
        sorted(df["year"].dropna().unique())
    )

    faculty = st.sidebar.multiselect(
        "Faculty",
        df["faculty"].dropna().unique()
    )

    status = st.sidebar.multiselect(
        "Status",
        df["status"].dropna().unique()
    )

    # --------------------------
    # APPLY FILTERS
    # --------------------------
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
    year_data = filtered_df.groupby("year").size().reset_index(name="count")
    fig1 = px.bar(year_data, x="year", y="count")
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("📊 Category Distribution")
    fig2 = px.pie(filtered_df, names="category")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("📊 Quartile Distribution")
    q_data = filtered_df["quartile"].value_counts().reset_index()
    q_data.columns = ["quartile", "count"]
    fig3 = px.bar(q_data, x="quartile", y="count")
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("👨‍🏫 Publications by Faculty")
    fac_data = filtered_df["faculty"].value_counts().reset_index()
    fac_data.columns = ["faculty", "count"]
    fig4 = px.bar(fac_data, x="faculty", y="count")
    st.plotly_chart(fig4, use_container_width=True)

    # --------------------------
    # SEARCH + TABLE
    # --------------------------
    st.subheader("📋 All Publications")

    search = st.text_input("Search")

    if search:
        filtered_df = filtered_df[
            filtered_df.apply(lambda row: search.lower() in str(row).lower(), axis=1)
        ]

    st.dataframe(filtered_df, use_container_width=True)

else:
    st.info("⬆️ Upload your Excel file to view dashboard")
