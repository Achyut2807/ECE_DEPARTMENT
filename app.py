import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")
st.title("📊 Publication Dashboard")

file = "Protected_Deparment_FactSheet-2.xlsx"

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

def parse_amount(val):
    """Convert amount strings like '1,949,400' or '27,73,800' to float. Returns None if invalid."""
    import math
    if val is None:
        return None
    s = str(val).strip().replace(",", "").replace("INR", "").strip()
    if s.lower() in ("nan", "", "-", "n/a"):
        return None
    try:
        result = float(s)
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    except ValueError:
        return None

# ------------------ PATENT EXTRACTOR ------------------

def extract_patents(sheet_name):
    raw = pd.read_excel(file, sheet_name=sheet_name, header=None)

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

    header_row = raw.iloc[header_row_idx]
    valid_cols = [c for c in raw.columns if str(header_row[c]).strip() not in ("nan", "")]

    patent_rows = []
    for i in range(header_row_idx + 1, len(raw)):
        row = raw.iloc[i]
        if row[valid_cols].isna().all():
            break
        patent_rows.append(row[valid_cols].values)

    if not patent_rows:
        return pd.DataFrame()

    col_names = [str(header_row[c]).strip() for c in valid_cols]
    patent_data = pd.DataFrame(patent_rows, columns=col_names)

    title_col = None
    inventors_col = None
    for col in patent_data.columns:
        col_lower = col.lower().strip()
        if col_lower == "title":
            title_col = col
        elif "inoveter" in col_lower or "inventor" in col_lower:
            inventors_col = col

    if title_col:
        patent_data = patent_data[
            patent_data[title_col].astype(str).str.strip().str.lower().ne("nan") &
            patent_data[title_col].astype(str).str.strip().ne("")
        ]

    patent_data["_title_col"] = title_col
    patent_data["_inventors_col"] = inventors_col
    return patent_data

# ------------------ GRANT EXTRACTOR ------------------

def extract_grants(sheet_name):
    """
    Extracts government grants (Grant Amount) and industry consultancy
    (Consultancy Amount) from a faculty sheet.
    Returns a list of dicts: Year, Agency, Amount, Title, Type.
    """
    raw = pd.read_excel(file, sheet_name=sheet_name, header=None)
    results = []

    grant_header_idx = None
    consult_header_idx = None

    for i, row in raw.iterrows():
        for cell in row.values:
            cell_s = str(cell).lower()
            if "grant amount" in cell_s and grant_header_idx is None:
                grant_header_idx = i
            if "consultancy amount" in cell_s and consult_header_idx is None:
                consult_header_idx = i

    def parse_block(header_idx, amount_keyword, type_label, year_keyword, agency_keyword):
        if header_idx is None:
            return
        header_row = raw.iloc[header_idx]

        col_map = {}
        for c in raw.columns:
            val = str(header_row[c]).strip().lower()
            if val not in ("nan", ""):
                col_map[c] = val

        year_col = amount_col = agency_col = title_col = None
        for c, name in col_map.items():
            if year_keyword in name and year_col is None:
                year_col = c
            if amount_keyword in name and amount_col is None:
                amount_col = c
            if agency_keyword in name and agency_col is None:
                agency_col = c
            if "title" in name and title_col is None:
                title_col = c

        valid = list(col_map.keys())
        for i in range(header_idx + 1, len(raw)):
            row = raw.iloc[i]
            if row[valid].isna().all():
                break
            amt_raw = row[amount_col] if amount_col is not None else None
            amount = parse_amount(amt_raw)
            if amount is None:
                continue
            year_val = row[year_col] if year_col is not None else None
            year = None
            try:
                year = int(float(str(year_val)))
            except (ValueError, TypeError):
                pass
            agency = str(row[agency_col]).strip() if agency_col is not None else "N/A"
            title  = str(row[title_col]).strip()  if title_col  is not None else "N/A"
            results.append({
                "Year":   year,
                "Agency": agency,
                "Amount": amount,
                "Title":  title,
                "Type":   type_label,
            })

    parse_block(grant_header_idx,   "grant amount",       "Government Grant",
                "grant year",              "funding agency")
    parse_block(consult_header_idx, "consultancy amount", "Industry Consultancy",
                "consultancy grant year",  "funding industry")

    return results

# ------------------ BUILD ALL-FACULTY GRANT TABLE ------------------

all_grants = []
for name in sheets.keys():
    for g in extract_grants(name):
        g["Faculty"] = name
        all_grants.append(g)

df_grants_all = pd.DataFrame(all_grants) if all_grants else pd.DataFrame(
    columns=["Year", "Agency", "Amount", "Title", "Type", "Faculty"])

# ------------------ ALL DATA (publications) ------------------

all_data = []
for name, df_temp in sheets.items():
    df_temp = df_temp.dropna(how="all")
    df_temp = clean_columns(df_temp)
    df_temp["Faculty"] = name

    year_col  = get_column(df_temp, ["year"])
    cat_col   = get_column(df_temp, ["category"])
    title_col = get_column(df_temp, ["title"])

    df_temp["Publication Year"]     = pd.to_numeric(df_temp[year_col], errors="coerce") if year_col else None
    df_temp["Publication Category"] = df_temp[cat_col]  if cat_col  else None
    df_temp["Publication Title"]    = df_temp[title_col] if title_col else "N/A"
    all_data.append(df_temp)

df_all = pd.concat(all_data, ignore_index=True)
df_all["Count"] = 1

# ================================================================
# ALL PAGE
# ================================================================

if page == "All":

    st.header("📊 Department Overview")

    total_grant = df_grants_all["Amount"].sum() if not df_grants_all.empty else 0
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Records",        len(df_all))
    col2.metric("Total Faculty",        df_all["Faculty"].nunique())
    col3.metric("Total Grants Received", f"Rs.{total_grant:,.0f}")

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

    # ---------- TOTAL GRANT PER YEAR ----------
    st.subheader("💰 Total Grant Amount per Year")

    if df_grants_all.empty or df_grants_all["Year"].isna().all():
        st.write("No grant data available.")
    else:
        df_gy = df_grants_all.dropna(subset=["Year"]).copy()
        df_gy["Year"] = df_gy["Year"].astype(int)

        df_gy_grouped = (
            df_gy.groupby(["Year", "Type"])["Amount"]
            .sum()
            .reset_index()
        )

        fig_grant = px.bar(
            df_gy_grouped,
            x="Year",
            y="Amount",
            color="Type",
            barmode="group",
            labels={"Amount": "Grant Amount (Rs.)", "Year": "Year"},
            color_discrete_map={
                "Government Grant":     "#4C78A8",
                "Industry Consultancy": "#F58518",
            },
        )
        fig_grant.update_layout(yaxis_tickformat=",")
        st.plotly_chart(fig_grant, use_container_width=True)

        # Summary table
        df_gy_total = (
            df_gy.groupby("Year")["Amount"]
            .sum()
            .reset_index()
            .sort_values("Year")
        )
        df_gy_total.columns = ["Year", "Total Amount"]
        df_gy_total["Total Amount"] = df_gy_total["Total Amount"].apply(lambda x: f"Rs.{x:,.0f}")
        st.dataframe(df_gy_total, use_container_width=True, hide_index=True)

# ================================================================
# INDIVIDUAL PAGE
# ================================================================

else:

    sheet_name = st.sidebar.selectbox("Select Faculty", list(sheets.keys()))
    df = sheets[sheet_name]
    df = df.dropna(how="all")
    df = clean_columns(df)

    title_col      = None
    patent_cat_col = None
    year_col       = None
    cat_col        = None
    status_col     = None
    quartile_col   = None

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

    df["Publication Year"]     = pd.to_numeric(df[year_col], errors="coerce") if year_col else None
    df["Publication Category"] = df[cat_col]  if cat_col  else None
    df["Publication Title"]    = df[title_col] if title_col else "N/A"
    df["Status"]               = df[status_col]   if status_col   else "Unknown"
    df["Quartile"]             = df[quartile_col] if quartile_col else "Unknown"

    df = df[df["Publication Year"].notna()]
    df["Publication Year"] = df["Publication Year"].astype(int)
    df["Count"] = 1

    # KPIs
    grants_this     = extract_grants(sheet_name)
    total_ind_grant = sum(g["Amount"] for g in grants_this)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Publications",   len(df))
    col2.metric("Published Papers",     len(df[df["Status"] == "Published"]))
    col3.metric("Total Grant Received", f"Rs.{total_ind_grant:,.0f}")

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

    # ------------------ PATENTS ------------------
    st.subheader("📜 Patents")
    patents_df = extract_patents(sheet_name)
    if patents_df.empty:
        st.write("No patents found for this faculty member.")
    else:
        title_col_pat     = patents_df["_title_col"].iloc[0]
        inventors_col_pat = patents_df["_inventors_col"].iloc[0]
        for _, row in patents_df.iterrows():
            title     = str(row[title_col_pat]).strip()     if title_col_pat     else "N/A"
            inventors = str(row[inventors_col_pat]).strip() if inventors_col_pat and inventors_col_pat in row.index else "N/A"
            category  = str(row.get("Patent Category", "N/A")).strip()
            year      = str(row.get("Year", "N/A")).strip()
            st.write(f"• **{title}**  |  Category: {category}  |  Year: {year}  |  Inventors: {inventors}")

    # ------------------ GRANTS ------------------
    st.subheader("💰 Grants & Consultancy")

    if not grants_this:
        st.write("No grant or consultancy data found for this faculty member.")
    else:
        df_ind = pd.DataFrame(grants_this)
        gov    = df_ind[df_ind["Type"] == "Government Grant"]
        cons   = df_ind[df_ind["Type"] == "Industry Consultancy"]

        if not gov.empty:
            st.markdown("**🏛️ Government / Research Grants**")
            for _, row in gov.iterrows():
                year   = int(row["Year"]) if row["Year"] is not None else "N/A"
                amount = f"Rs.{row['Amount']:,.0f}"
                st.write(f"• **{row['Title']}**")
                st.write(f"  &nbsp;&nbsp;&nbsp;Agency: {row['Agency']}  |  Year: {year}  |  Amount: **{amount}**")

        if not cons.empty:
            st.markdown("**🏭 Industry Consultancy**")
            for _, row in cons.iterrows():
                year   = int(row["Year"]) if row["Year"] is not None else "N/A"
                amount = f"Rs.{row['Amount']:,.0f}"
                st.write(f"• **{row['Title']}**")
                st.write(f"  &nbsp;&nbsp;&nbsp;Industry: {row['Agency']}  |  Year: {year}  |  Amount: **{amount}**")
