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

    st.subheader("📊 Journal vs Conference")

    df_cat = df_all[
        df_all["Publication Category"].astype(str)
        .str.contains("Journal|Conference", case=False, na=False)
    ]

    if not df_cat.empty:
        df_cat = df_cat.groupby("Publication Category")["Count"].sum().reset_index()
        fig2 = px.pie(df_cat, names="Publication Category", values="Count")
        st.plotly_chart(fig2, use_container_width=True)

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

    # ------------------ STRICT COLUMN FIX ------------------

    title_col = None
    patent_cat_col = None
    year_col = None
    cat_col = None
    status_col = None
    quartile_col = None

    for col in df.columns:
        col_lower = col.lower().strip()

        # ✅ FIXED: handle both cases
        if col_lower in ["title", "publication title"]:
            title_col = col

        elif "patent category" in col_lower:
            patent_cat_col = col

        elif "year" in col_lower:
            year_col = col

        elif "category" in col_lower:
            cat_col = col

        elif "status" in col_lower:
            status_col = col

        elif "quartile" in col_lower:
            quartile_col = col

    # ------------------ CREATE CLEAN DATA ------------------

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
        df_cat_chart = df.groupby("Publication Category")["Count"].sum().reset_index()
        fig2 = px.pie(df_cat_chart, names="Publication Category", values="Count")
        st.plotly_chart(fig2, use_container_width=True)

    # ------------------ TEXT SECTIONS ------------------

    st.subheader("📜 Patents")

    patents = df[
        df["Publication Category"].astype(str)
        .str.contains("Patent", case=False, na=False)
    ]

    for _, row in patents.iterrows():
        title = row[title_col] if title_col else "N/A"
        category = row[patent_cat_col] if patent_cat_col else "N/A"

        st.write(f"• {title}  |  Category: {category}")
