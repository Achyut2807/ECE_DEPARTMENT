import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")

st.title("📊 Publication Dashboard")

file = "Protected_Deparment_FactSheet-2.xlsx"

# Load sheets with header=1 (row index 1 as header)
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

# ------------------ PATENT PARSER (FIX) ------------------
# The patent section in each sheet is an embedded sub-table with its own
# headers: "Year", "Patent Category", "Title", "List of Inoveters".
# We detect the sub-header row and re-parse that block independently.

def extract_patents(sheet_name):
    """
    Re-reads the raw sheet (no header skip) and locates the patent sub-table
    by finding the row that contains 'Patent Category' as a cell value.
    Returns a DataFrame with columns: Year, Patent Category, Title, List of Inventors.
    """
    raw = pd.read_excel(file, sheet_name=sheet_name, header=None)

    # Find the row index where the patent sub-header lives
    header_row_idx = None
    for i, row in raw.iterrows():
        for cell in row.values:
            if "patent category" in str(cell).lower():
                header_row_idx = i
                break
        if header_row_idx is not None:
            break

    if header_row_idx is None:
        return pd.DataFrame()

    # Extract only the columns that have values in the header row
    header_row = raw.iloc[header_row_idx]
    valid_cols = [c for c in raw.columns if str(header_row[c]).strip() not in ("nan", "")]

    # Slice data rows below the header
    patent_data = raw.iloc[header_row_idx + 1:][valid_cols].copy()
    patent_data.columns = [str(header_row[c]).strip() for c in valid_cols]
    patent_data = patent_data.dropna(how="all")

    # Normalise column names so we can rely on them
    patent_data.columns = [c.strip() for c in patent_data.columns]

    # Drop rows that look like another header repetition
    patent_data = patent_data[~patent_data.apply(
        lambda r: r.astype(str).str.lower().str.contains("patent category").any(), axis=1
    )]

    # Find the Title column (handles "Title" and similar variants)
    title_col = None
    inventors_col = None
    for col in patent_data.columns:
        col_lower = col.lower()
        if col_lower == "title":
            title_col = col
        elif "inoveter" in col_lower or "inventor" in col_lower:
            inventors_col = col

    # Keep only rows where Title is not blank
    if title_col:
        patent_data = patent_data[patent_data[title_col].astype(str).str.strip().replace("nan", "").ne("")]

    patent_data["_title_col"] = title_col
    patent_data["_inventors_col"] = inventors_col

    return patent_data


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

    # ------------------ PATENTS SECTION (FIXED) ------------------

    st.subheader("📜 Patents")

    # Use the dedicated patent extractor that reads the embedded sub-table
    patents_df = extract_patents(sheet_name)

    if patents_df.empty:
        st.write("No patents found for this faculty member.")
    else:
        title_col_pat = patents_df["_title_col"].iloc[0]
        inventors_col_pat = patents_df["_inventors_col"].iloc[0]

        for _, row in patents_df.iterrows():
            # ✅ FIX: Read "Title" from the patent sub-table's own "Title" column,
            #         NOT from the main sheet's "Publication Title" column (which
            #         was actually aligned with "List of Inoveters" in the sub-table).
            title = str(row[title_col_pat]).strip() if title_col_pat else "N/A"
            inventors = str(row[inventors_col_pat]).strip() if inventors_col_pat and inventors_col_pat in row.index else "N/A"
            category = str(row.get("Patent Category", "N/A")).strip()
            year = str(row.get("Year", "N/A")).strip()

            st.write(f"• **{title}**  |  Category: {category}  |  Year: {year}  |  Inventors: {inventors}")
