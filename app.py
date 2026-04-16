import streamlit as st
import pandas as pd
import plotly.express as px
import re

st.set_page_config(layout="wide", page_title="ECE Faculty Dashboard", page_icon="📡")

# ──────────────────────────────────────────────
#   UTILITIES (Currency & Section Extraction)
# ──────────────────────────────────────────────

def clean_currency(val):
    """Converts strings like '24,97,762', '2.7 Lakhs', or '₹ 1,00,000' to a float."""
    if pd.isna(val) or str(val).strip().lower() in ["nan", "na", "", "---", "none"]:
        return 0.0
    # Remove symbols and commas
    s = str(val).lower().replace(",", "").replace("inr", "").replace("rs", "").replace("₹", "").strip()
    
    multiplier = 1
    if "lakh" in s or "lac" in s:
        multiplier = 100000
    
    # Extract numeric part
    match = re.search(r"(\d+\.?\d*)", s)
    if match:
        try:
            return float(match.group(1)) * multiplier
        except:
            return 0.0
    return 0.0

def find_row(df_str, keyword):
    mask = df_str.apply(lambda col: col.str.contains(keyword, case=False, na=False)).any(axis=1)
    hits = df_str[mask].index
    return int(hits[0]) if len(hits) > 0 else None

def dedup_cols(cols):
    seen, result = {}, []
    for c in cols:
        c = str(c).strip() if not pd.isna(c) else "nan"
        if c in seen:
            seen[c] += 1
            result.append(f"{c}_{seen[c]}")
        else:
            seen[c] = 0
            result.append(c)
    return result

def extract_section(df, start_kw, end_kw):
    df_str = df.astype(str)
    start = find_row(df_str, start_kw)
    end   = find_row(df_str, end_kw) if end_kw else len(df)
    if start is None: return pd.DataFrame()

    header_row = None
    for offset in range(1, 6):
        if start + offset >= len(df): break
        vals = [v for v in df.iloc[start + offset].tolist() if str(v) not in ("nan", "")]
        if len(vals) >= 3:
            header_row = start + offset
            break
    if header_row is None: return pd.DataFrame()

    sub = df.iloc[header_row + 1 : end].copy()
    sub.columns = dedup_cols(df.iloc[header_row].tolist())
    sub = sub.dropna(how="all")
    
    if not sub.empty:
        first_col = sub.columns[0]
        # Keep rows that contain a digit (Sl. No.)
        sub = sub[sub[first_col].astype(str).str.contains(r"\d", na=False)]
    return sub.reset_index(drop=True)

def get_col(df, keywords):
    for c in df.columns:
        if any(k.lower() in str(c).lower() for k in keywords):
            return c
    return None

def fmt_inr(amount):
    """Format numbers as Indian Rupees (Lakhs/Crores)."""
    if pd.isna(amount) or amount == 0:
        return "₹0"
    if amount >= 1_00_00_000:
        return f"₹{amount/1_00_00_000:.2f} Cr"
    elif amount >= 1_00_000:
        return f"₹{amount/1_00_000:.2f} L"
    else:
        return f"₹{amount:,.0f}"

# ──────────────────────────────────────────────
#   DATA LOADING
# ──────────────────────────────────────────────

@st.cache_data
def load_data(path):
    raw = pd.read_excel(path, sheet_name=None, header=None)
    data = {}
    for name, df in raw.items():
        if name == "Sheet1": continue
        data[name] = {
            "pub":      extract_section(df, "Publication Details", "Patent/Copyright Detail"),
            "patent":   extract_section(df, "Patent/Copyright Detail", "Project"),
            "grant":    extract_section(df, "Project", "Industry Consultancy"),
            "consult":  extract_section(df, "Industry Consultancy", "Workshop/Seminar"),
            "workshop": extract_section(df, "Workshop/Seminar", "Student Acheivements"),
            "stud_ach": extract_section(df, "Student Acheivements", "Expert/Invited Talk"),
            "award":    extract_section(df, "Award Recived", "Membership"),
        }
    return data

FILE = "Protected_Deparment_FactSheet-2.xlsx"
try:
    data_dict = load_data(FILE)
except Exception as e:
    st.error(f"Please ensure '{FILE}' is in the folder. Error: {e}")
    st.stop()

# ──────────────────────────────────────────────
#   GLOBAL PROCESSING
# ──────────────────────────────────────────────

all_fac = sorted(data_dict.keys())
grant_list, consult_list, pub_list, pat_list = [], [], [], []

for fac, tables in data_dict.items():
    for lst, key in [(grant_list, "grant"), (consult_list, "consult"), (pub_list, "pub"), (pat_list, "patent")]:
        t = tables[key].copy()
        if not t.empty:
            t["Faculty"] = fac
            lst.append(t)

df_grants = pd.concat(grant_list, ignore_index=True) if grant_list else pd.DataFrame()
df_consult = pd.concat(consult_list, ignore_index=True) if consult_list else pd.DataFrame()
df_pubs = pd.concat(pub_list, ignore_index=True) if pub_list else pd.DataFrame()
df_pats = pd.concat(pat_list, ignore_index=True) if pat_list else pd.DataFrame()

# Clean Project Total (Unique across department)
def compute_unique_grant_total(gr_df, co_df):
    unique_entries = []
    for df in [gr_df, co_df]:
        if df.empty: continue
        amt_col = get_col(df, ["amount"])
        title_col = get_col(df, ["title"])
        if amt_col and title_col:
            for _, r in df.iterrows():
                amt = clean_currency(r[amt_col])
                t_norm = re.sub(r'[^a-z0-9]', '', str(r[title_col]).lower())
                if t_norm: unique_entries.append({"t": t_norm, "a": amt})
    if not unique_entries: return 0.0
    return pd.DataFrame(unique_entries).drop_duplicates(subset=["t", "a"])["a"].sum()

total_dept_grant = compute_unique_grant_total(df_grants, df_consult)

# Filter 2022+ Publications
YEAR_COL = get_col(df_pubs, ["year"])
CAT_COL = get_col(df_pubs, ["category"])
if YEAR_COL and not df_pubs.empty:
    df_pubs[YEAR_COL] = pd.to_numeric(df_pubs[YEAR_COL], errors="coerce")
    f_pubs = df_pubs[(df_pubs[YEAR_COL] >= 2022) & df_pubs[CAT_COL].astype(str).str.contains("Journal|Conference", case=False, na=False)].copy()
else:
    f_pubs = pd.DataFrame()

# ──────────────────────────────────────────────
#   UI - DASHBOARD
# ──────────────────────────────────────────────

st.sidebar.title("📡 ECE PDEU")
view = st.sidebar.radio("🗂️ Navigate", ["📊 Overall Dashboard", "👤 Individual Profile"])

if view == "📊 Overall Dashboard":
    st.title("📊 ECE Department Dashboard")
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("📄 Publications (22+)", len(f_pubs))
    k2.metric("🔬 Patents (22+)",     len(df_pats))
    k3.metric("🏦 Unique Projects",   len(df_grants.drop_duplicates(subset=[get_col(df_grants, ['title'])])) if not df_grants.empty else 0)
    k4.metric("💰 Total Grant Amount", fmt_inr(total_dept_grant))

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📈 Publication Trend")
        if not f_pubs.empty and YEAR_COL:
            trend = f_pubs.groupby(YEAR_COL).size().reset_index(name="Count")
            st.plotly_chart(px.line(trend, x=YEAR_COL, y="Count", markers=True), use_container_width=True)
    with c2:
        st.subheader("💰 Grant Amount by Faculty")
        rows = []
        for fac in all_fac:
            f_total = 0
            for df in [df_grants, df_consult]:
                if df.empty: continue
                fac_df = df[df["Faculty"] == fac]
                ac = get_col(fac_df, ["amount"])
                if ac: f_total += fac_df[ac].apply(clean_currency).sum()
            rows.append({"Faculty": fac, "Amount": f_total})
        grant_df_fac = pd.DataFrame(rows).sort_values("Amount", ascending=False).query("Amount > 0")
        if not grant_df_fac.empty:
            st.plotly_chart(px.bar(grant_df_fac, x="Faculty", y="Amount", text=grant_df_fac["Amount"].apply(fmt_inr)), use_container_width=True)

    st.divider()
    st.subheader("🏆 Faculty Productivity")
    p_cnt = f_pubs["Faculty"].value_counts() if not f_pubs.empty else pd.Series()
    g_cnt = df_grants["Faculty"].value_counts() if not df_grants.empty else pd.Series()
    prod = pd.DataFrame({"Papers": p_cnt, "Grants": g_cnt}).fillna(0).astype(int)
    prod = prod.reindex(all_fac, fill_value=0).sort_values("Papers", ascending=False).reset_index().rename(columns={"index": "Faculty"})
    st.plotly_chart(px.bar(prod, x="Faculty", y=["Papers", "Grants"], barmode="stack"), use_container_width=True)

# ──────────────────────────────────────────────
#   UI - INDIVIDUAL PROFILE
# ──────────────────────────────────────────────

else:
    fac = st.sidebar.selectbox("Select Faculty", all_fac)
    tabs = data_dict[fac]
    
    # Calculate Individual Total
    f_grant_total = 0
    for k in ["grant", "consult"]:
        sec = tabs[k]
        ac = get_col(sec, ["amount"])
        if ac: f_grant_total += sec[ac].apply(clean_currency).sum()

    st.title(f"👤 {fac}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📄 Total Papers", len(tabs["pub"]))
    m2.metric("🔬 Patents",      len(tabs["patent"]))
    m3.metric("🏦 Funded Projects", len(tabs["grant"]))
    m4.metric("💰 Total Grant",   fmt_inr(f_grant_total))

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🎖️ Awards & Student Achievements")
        for key, label in [("award", "Award"), ("stud_ach", "Student Achievement")]:
            df_sec = tabs[key]
            if not df_sec.empty:
                st.markdown(f"**{label}s:**")
                # Look for Detail or Name columns
                d_col = get_col(df_sec, ["detail", "award", "achievement", "name"])
                if d_col:
                    for _, r in df_sec.iterrows(): st.write(f"• {r[d_col]}")
            else:
                st.info(f"No {label}s on record.")
                
    with col2:
        st.subheader("🏦 Projects & Consultancy")
        for key, label in [("grant", "Research Project"), ("consult", "Consultancy")]:
            df_sec = tabs[key]
            if not df_sec.empty:
                st.markdown(f"**{label}s:**")
                t_col = get_col(df_sec, ["title"])
                a_col = get_col(df_sec, ["amount"])
                for _, r in df_sec.iterrows():
                    amt = fmt_inr(clean_currency(r[a_col]))
                    st.write(f"• **{r[t_col]}** ({amt})")
            else:
                st.info(f"No {label}s on record.")

    with st.expander("📋 Full Publication List"):
        if not tabs["pub"].empty:
            st.dataframe(tabs["pub"], use_container_width=True)
