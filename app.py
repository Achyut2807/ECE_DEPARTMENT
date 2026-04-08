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
    # TRY DIFFERENT HEADER LEVELS (AUTO FIX)
    # --------------------------
    def load_data(file):
        for i in range(5):  # try first 5 rows as header
            try:
                df = pd.read_excel(file, header=i)
                df.columns = df.columns.astype(str).str.strip().str.lower()

                # check if meaningful columns exist
                if any("year" in col for col in df.columns):
                    return df
            except:
                continue
        return pd.read_excel(file)

    df = load_data(uploaded_file)

    # --------------------------
    # CLEAN COLUMN NAMES
    # --------------------------
    df.columns = df.columns.astype(str).str.strip().str.lower()

    st.write("Detected Columns:", df.columns.tolist())

    # --------------------------
    # AUTO COLUMN DETECTION
    # --------------------------
    def find_col(keywords):
        for col in df.columns:
            for key in keywords:
                if key in col:
                    return col
        return None

    title_col = find_col(["title", "publication"])
    faculty_col = find_col(["faculty", "author"])
    year_col = find_col(["year"])
    category_col = find_col(["category", "type"])
    status_col = find_col(["status"])
    quartile_col = find_col(["quartile", "q"])

    # --------------------------
    # VALIDATION
    # --------------------------
    if not year_col:
        st.error("❌ Could not detect 'Year' column. Please check Excel format.")
        st.stop()

    # --------------------------
    # CLEAN DATA
    # --------------------------
    df = df.dropna(how="all")  # remove empty rows

    if title_col:
        df = df.dropna(subset=[title_col])

    # --------------------------
    # SIDEBAR FILTERS
    # --------------------------
    st.sidebar.header("🔍 Filters")

    if category_col:
        category = st.sidebar.multiselect(
            "Category", df[category_col].dropna().unique()
        )
    else:
        category = []

    year = st.sidebar.multiselect(
        "Year", sorted(df[year_col].dropna().unique())
    )

    if faculty_col:
        faculty = st.sidebar.multiselect(
            "Faculty", df[faculty_col].dropna().unique()
        )
    else:
        faculty = []

    if status_col:
        status = st.sidebar.multiselect(
            "Status", df[status_col].dropna().unique()
        )
    else:
        status = []

    # --------------------------
    # APPLY FILTERS
    # --------------------------
    filtered_df = df.copy()

    if category_col and category:
        filtered_df = filtered_df[filtered_df[category_col].isin(category)]

    if year:
        filtered_df = filtered_df[filtered_df[year_col].isin(year)]

    if faculty_col and faculty:
        filtered_df = filtered_df[filtered_df[faculty_col].isin(faculty)]

    if status_col and status:
        filtered_df = filtered_df[filtered_df[status_col].isin(status)]

    # --------------------------
    # METRICS
    # --------------------------
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Papers", len(filtered_df))

    if category_col:
        col2.metric("Journals", len(filtered_df[filtered_df[category_col] == "Journal"]))
        col3.metric("Conferences", len(filtered_df[filtered_df[category_col] == "Conference"]))
    else:
        col2.metric("Journals", "N/A")
        col3.metric("Conferences", "N/A")

    if faculty_col:
        col4.metric("Faculty", filtered_df[faculty_col].nunique())
    else:
        col4.metric("Faculty", "N/A")

    # --------------------------
    # CHARTS
    # --------------------------
    st.subheader("📈 Publications by Year")
    year_data = filtered_df.groupby(year_col).size().reset_index(name="count")
    fig1 = px.bar(year_data, x=year_col, y="count")
    st.plotly_chart(fig1, use_container_width=True)

    if category_col:
        st.subheader("📊 Category Distribution")
        fig2 = px.pie(filtered_df, names=category_col)
        st.plotly_chart(fig2, use_container_width=True)

    if quartile_col:
        st.subheader("📊 Quartile Distribution")
        q_data = filtered_df[quartile_col].value_counts().reset_index()
        q_data.columns = ["quartile", "count"]
        fig3 = px.bar(q_data, x="quartile", y="count")
        st.plotly_chart(fig3, use_container_width=True)

    if faculty_col:
        st.subheader("👨‍🏫 Publications by Faculty")
        fac_data = filtered_df[faculty_col].value_counts().reset_index()
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
