import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")

st.title("📊 Publication Dashboard")

file = "Protected_Deparment_FactSheet-2.xlsx"

# Load data correctly
sheets = pd.read_excel(file, sheet_name=None, header=1)

# Sidebar
st.sidebar.header("Controls")
sheet_name = st.sidebar.selectbox("Select Faculty", list(sheets.keys()))

df = sheets[sheet_name]

# Clean
df = df.dropna(how="all")
df.columns = df.columns.str.strip()
df["Count"] = 1

# Sidebar filters
year = st.sidebar.multiselect(
    "Select Year",
    df["Publication Year"].dropna().unique()
)

if year:
    df = df[df["Publication Year"].isin(year)]

# KPIs
col1, col2 = st.columns(2)

col1.metric("Total Publications", len(df))
col2.metric("Published Papers", len(df[df["Status"] == "Published"]))

# Charts
col1, col2 = st.columns(2)

with col1:
    st.subheader("Publications per Year")
    fig1 = px.bar(df, x="Publication Year", y="Count")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("Category Distribution")
    fig2 = px.pie(df, names="Publication Category", values="Count")
    st.plotly_chart(fig2, use_container_width=True)

# Second row
col3, col4 = st.columns(2)

with col3:
    st.subheader("Status")
    fig3 = px.bar(df, x="Status", y="Count")
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.subheader("Quartile Analysis")
    fig4 = px.bar(df, x="Quartile", y="Count")
    st.plotly_chart(fig4, use_container_width=True)