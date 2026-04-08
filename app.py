import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")

st.title("📊 Publication Dashboard")

file = "Protected_Deparment_FactSheet-2.xlsx"

# Load sheets
sheets = pd.read_excel(file, sheet_name=None, header=1)

# ------------------ SIDEBAR ------------------
st.sidebar.header("Controls")
page = st.sidebar.selectbox("Select View", ["Individual", "All"])

# ------------------ HELPERS ------------------

def clean_columns(df):
    df.columns = [str(col).strip() for col in df.columns]
    return df

def get_column(df, keywords):
    for col in df.columns:
        for key in keywords:
            if key.lower() in col.lower():
                return col
    return None

# ------------------ ALL DATA ------------------

all_data = []

for name, df_temp in sheets.items():
    df_temp = df_temp.dropna(how="all")
    df_temp = clean_columns(df_temp)

    df_temp["Faculty"] = name

    year_col = get_column(df_temp, ["year"])
    cat_col = get_column(df_temp, ["category"])
    title_col = get_column(df_temp, ["title"])

    df_temp["Publication Year"] = pd.to_numeric(df_temp[year_col], errors="coerce") if year_col else None
    df_temp["Publication Category"] = df_temp[cat_col] if cat_col else None
    df_temp["Publication Title"] = df_temp[title_col] if title_col else "N/A"

    all_data.append(df_temp)

df_all = pd.concat(all_data, ignore_index=True)
df_all["Count"] = 1

# ------------------ ALL PAGE ------------------

if page == "All":

    st.header("📊 Department Overview")

    col1, col2 = st.columns(2)
    col1.metric("Total Records", len(df_all))
    col2.metric("Total Faculty", df_all["Faculty"].nunique())

    # 📈 TREND
    st.subheader("📈 Publication Trend")

    df_trend = df_all.dropna(subset=["Publication Year"]).copy()
    df_trend = df_trend[df_trend["Publication Year"] >= 2022]

    if not df_trend.empty:
        df_trend["Publication Year"] = df_trend["Publication Year"].astype(int)
        df_trend = df_trend.groupby("Publication Year")["Count"].sum().reset_index()

        fig = px.line(df_trend, x="Publication Year", y="Count", markers=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("No valid data from 2022 onwards")

    # 📊 CATEGORY
    st.subheader("📊 Journal vs Conference")

    df_cat = df_all[
        df_all["Publication Category"].astype(str)
        .str.contains("Journal|Conference", case=False, na=False)
    ]

    if not df_cat.empty:
        df_cat = df_cat.groupby("Publication Category")["Count"].sum().reset_index()
        fig2 = px.pie(df_cat, names="Publication Category", values="Count")
        st.plotly_chart(fig2, use_container_width=True)

    # 🏆 FACULTY PRODUCTIVITY
    st.subheader("🏆 Faculty Productivity")

    df_fac = df_all.groupby("Faculty")["Count"].sum().reset_index()
    df_fac = df_fac.sort_values(by="Count", ascending=False)

    fig3 = px.bar(df_fac, x="Faculty", y="Count")
    st.plotly_chart(fig3, use_container_width=True)

# ------------------ INDIVIDUAL PAGE ------------------

else:

    sheet_name = st.sidebar.selectbox("Select Faculty", list(sheets.keys()))
    df = sheets[sheet_name]

    df = df.dropna(how="all")
    df = clean_columns(df)

    year_col = get_column(df, ["year"])
    cat_col = get_column(df, ["category"])
    title_col = get_column(df, ["title"])
    status_col = get_column(df, ["status"])
    quartile_col = get_column(df, ["quartile"])

    df["Publication Year"] = pd.to_numeric(df[year_col], errors="coerce") if year_col else None
    df["Publication Category"] = df[cat_col] if cat_col else None
    df["Publication Title"] = df[title_col] if title_col else "N/A"
    df["Status"] = df[status_col] if status_col else "Unknown"
    df["Quartile"] = df[quartile_col] if quartile_col else "Unknown"

    df = df[df["Publication Year"].notna()]
    df["Publication Year"] = df["Publication Year"].astype(int)

    df["Count"] = 1

    # KPIs
    col1, col2 = st.columns(2)
    col1.metric("Total Publications", len(df))
    col2.metric("Published Papers", len(df[df["Status"] == "Published"]))

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Publications per Year")
        df_year = df.groupby("Publication Year")["Count"].sum().reset_index()
        fig1 = px.bar(df_year, x="Publication Year", y="Count")
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader("📊 Category Distribution")
        df_cat = df.groupby("Publication Category")["Count"].sum().reset_index()
        fig2 = px.pie(df_cat, names="Publication Category", values="Count")
        st.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        st.subheader("📌 Status Analysis")
        df_status = df.groupby("Status")["Count"].sum().reset_index()
        fig3 = px.bar(df_status, x="Status", y="Count")
        st.plotly_chart(fig3, use_container_width=True)

    with col4:
        st.subheader("🏆 Quartile Analysis")
        df_q = df.groupby("Quartile")["Count"].sum().reset_index()
        fig4 = px.bar(df_q, x="Quartile", y="Count")
        st.plotly_chart(fig4, use_container_width=True)

    # ------------------ TEXT SECTIONS ------------------

    st.subheader("🏆 Achievements / Awards")
    achievements = df[df["Publication Category"].astype(str).str.contains("Award|Achievement", case=False, na=False)]
    for _, row in achievements.iterrows():
        st.write("•", row["Publication Title"])

    # ✅ FIXED PATENTS SECTION
    st.subheader("📜 Patents")

    patent_cat_col = get_column(df, ["patent category"])

    patents = df[
        df["Publication Category"].astype(str)
        .str.contains("Patent", case=False, na=False)
    ]

    for _, row in patents.iterrows():
        title = row["Publication Title"]

        category = (
            row[patent_cat_col]
            if patent_cat_col and patent_cat_col in df.columns
            else "N/A"
        )

        st.write(f"• {title}  |  Category: {category}")

    st.subheader("🎓 Workshops / Seminars")

    events = df[df["Publication Category"].astype(str).str.contains("Workshop|Seminar", case=False, na=False)]

    for _, row in events.iterrows():
        st.write("•", row["Publication Title"])
