import streamlit as st
import pandas as pd
import plotly.express as px

# --------------------------
# PAGE CONFIG
# --------------------------
st.set_page_config(layout="wide")
st.title("📊 ECE Department Publications Dashboard")

# --------------------------
# FILE UPLOAD
# --------------------------
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if uploaded_file:

    # --------------------------
    # LOAD DATA
    # --------------------------
    df = pd.read_excel(uploaded_file)

    # --------------------------
    # CLEAN COLUMN NAMES (IMPORTANT FIX)
    # --------------------------
    df.columns = df.columns.str.strip().str.lower()

    # Show columns (for debugging)
    st.write("Detected Columns:", df.columns.tolist())

    # --------------------------
    # AUTO DETECT COLUMNS (VERY IMPORTANT)
    # --------------------------
    def find_col(possible_names):
        for col in df.columns:
            for name in possible_names:
                if name in col:
                    return col
        return None

    category_col = find_col(["category", "type"])
    year_col = find_col(["year"])
    faculty_col = find_col(["faculty", "author"])
    status_col = find_col(["status"])
    quartile_col = find_col(["quartile", "q"])

    # --------------------------
    # HANDLE MISSING COLUMNS
    # --------------------------
    if not all([category_col, year_col, faculty_col]):
        st.error("❌ Required columns not found in Excel (category/year/faculty)")
        st.stop()

    # --------------------------
    # SIDEBAR FILTERS
    # --------------------------
    st.sidebar.header("🔍 Filters")

    category = st.sidebar.multiselect(
        "Category",
        options=df[category_col].dropna().unique()
    )

    year = st.sidebar.multiselect(
        "Year",
        options=sorted(df[year_col].dropna().unique())
    )

    faculty = st.sidebar.multiselect(
        "Faculty",
        options=df[faculty_col].dropna().unique()
    )

    status = st.sidebar.multiselect(
        "Status",
        options=df[status_col].dropna().unique() if status_col else []
    )

    # --------------------------
    # APPLY FILTERS
    # --------------------------
    filtered_df = df.copy()

    if category:
        filtered_df = filtered_df[filtered_df[category_col].isin(category)]

    if year:
        filtered_df = filtered_df[filtered_df[year_col].isin(year)]

    if faculty:
        filtered_df = filtered_df[filtered_df[faculty_col].isin(faculty)]

    if status and status_col:
        filtered_df = filtered_df[filtered_df[status_col].isin(status)]

    # --------------------------
    # METRICS
    # --------------------------
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Papers", len(filtered_df))
    col2.metric("Journals", len(filtered_df[filtered_df[category_col] == "Journal"]))
    col3.metric("Conferences", len(filtered_df[filtered_df[category_col] == "Conference"]))
    col4.metric("Faculty", filtered_df[faculty_col].nunique())

    # --------------------------
    # CHARTS
    # --------------------------

    st.subheader("📈 Publications by Year")
    year_chart = filtered_df.groupby(year_col).size().reset_index(name="count")
    fig1 = px.bar(year_chart, x=year_col, y="count", title="Publications per Year")
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("📊 Category Distribution")
    cat_chart = filtered_df[category_col].value_counts().reset_index()
    cat_chart.columns = ["category", "count"]
    fig2 = px.pie(cat_chart, names="category", values="count")
    st.plotly_chart(fig2, use_container_width=True)

    if quartile_col:
        st.subheader("📊 Quartile Distribution")
        q_chart = filtered_df[quartile_col].value_counts().reset_index()
        q_chart.columns = ["quartile", "count"]
        fig3 = px.bar(q_chart, x="quartile", y="count")
        st.plotly_chart(fig3, use_container_width=True)

    st.subheader("👨‍🏫 Publications by Faculty")
    fac_chart = filtered_df[faculty_col].value_counts().reset_index()
    fac_chart.columns = ["faculty", "count"]
    fig4 = px.bar(fac_chart, x="faculty", y="count")
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
