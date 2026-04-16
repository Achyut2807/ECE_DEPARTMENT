import streamlit as st
import pandas as pd
import plotly.express as px
import re

st.set_page_config(layout="wide", page_title="ECE Faculty Dashboard", page_icon="📡")

# ──────────────────────────────────────────────
#   UTILITIES
# ──────────────────────────────────────────────

def clean_currency(val):
    """Robustly convert strings like '2.7 Lakhs', '3,50,000' or '₹ 1,00,000' to float."""
    if pd.isna(val) or str(val).strip().lower() in ["nan", "na", "", "---"]:
        return 0.0
    
    # Remove commas and normalize
    s = str(val).lower().replace(",", "").replace("inr", "").replace("rs", "").replace("₹", "").strip()
    
    # Handle multipliers
    multiplier = 1
    if "lakh" in s or "lac" in s:
        multiplier = 100000
    
    # Extract numeric part using regex
    match = re.search(r"(\d+\.?\d*)", s)
    if match:
        try:
            return float(match.group(1)) * multiplier
        except:
            return 0.0
    return 0.0

def find_row(df_str, keyword):
    mask = df_str.apply(
        lambda col: col.str.contains(keyword, case=False, na=False)
    ).any(axis=1)
    hits = df_str[mask].index
    return int(hits[0]) if len(hits) > 0 else None

def dedup_cols(cols):
    seen, result = {}, []
    for c in cols:
        c = str(c).strip()
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
    if start is None:
        return pd.DataFrame()

    header_row = None
    for offset in range(1, 6):
        if start + offset >= len(df):
            break
        vals = [v for v in df.iloc[start + offset].tolist() if str(v) not in ("nan", "")]
        if len(vals) >= 3:
            header_row = start + offset
            break
    if header_row is None:
        return pd.DataFrame()

    data_end = end if end else len(df)
    sub = df.iloc[header_row + 1 : data_end].copy()
    sub.columns = dedup_cols(df.iloc[header_row].tolist())
    sub = sub.dropna(how="all")
    first_col = sub.columns[0]
    # Only keep rows that start with a serial number
    sub = sub[sub[first_col].astype(str).str.strip().str.match(r"^\d+$")]
    return sub.reset_index(drop=True)

def get_col(df, keywords):
    for c in df.columns:
        if any(k.lower() in c.lower() for k in keywords):
            return c
    return None

def safe_vc(series, label="Label"):
    vc = series.value_counts().reset_index()
    vc.columns = [label, "Count"]
    return vc

def fmt_inr(amount):
    """Format a number as Indian currency (₹ with lakhs/crores)."""
    if pd.isna(amount) or amount == 0:
        return "₹0"
    if amount >= 1_00_00_000:
        return f"₹{amount/1_00_00_000:.2f} Cr"
    elif amount >= 1_00_000:
        return f"₹{amount/1_00_00_000:.2f} L" # Note: Corrected L division if needed
        return f"₹{amount/1_00_000:.2f} L"
    else:
        return f"₹{amount:,.0f}"

def merge_grants_and_consult(grant_df, consult_df):
    frames = []
    if not grant_df.empty:
        g = grant_df.copy()
        g["Source"] = "Grant"
        frames.append(g)
    if not consult_df.empty:
        c = consult_df.copy()
        c["Source"] = "Consultancy"
        frames.append(c)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)

# ──────────────────────────────────────────────
#   DATA LOADING
# ──────────────────────────────────────────────

@st.cache_data
def load_data(path):
    raw = pd.read_excel(path, sheet_name=None, header=None)
    excluded = {"Sheet1"}
    data = {}
    for name, df in raw.items():
        if name in excluded:
            continue
        data[name] = {
            "pub":      extract_section(df, "Publication Details",                    "Patent/Copyright Detail"),
            "patent":   extract_section(df, "Patent/Copyright Detail",                 "Project"),
            "grant":    extract_section(df, "Project",                                 "Industry Consultancy"),
            "consult":  extract_section(df, "Industry Consultancy",                    "Workshop/Seminar/Conference Organised"),
            "workshop": extract_section(df, "Workshop/Seminar/Conference Organised",   "Student Acheivements"),
            "stud_ach": extract_section(df, "Student Acheivements",                    "Expert/Invited Talk"),
            "award":    extract_section(df, "Award Recived",                           "Membership"),
        }
    return data

FILE = "Protected_Deparment_FactSheet-2.xlsx"
try:
    data_dict = load_data(FILE)
except Exception as e:
    st.error(f"❌ Error: {e}")
    st.stop()

# ──────────────────────────────────────────────
#   GLOBAL DATAFRAMES
# ──────────────────────────────────────────────

all_fac = sorted(data_dict.keys())
pub_list, pat_list, grant_list, consult_list = [], [], [], []

for fac, tables in data_dict.items():
    for lst, key in [(pub_list, "pub"), (pat_list, "patent"), (grant_list, "grant"), (consult_list, "consult")]:
        t = tables[key].copy()
        if not t.empty:
            t["Faculty"] = fac
            lst.append(t)

df_pubs    = pd.concat(pub_list,     ignore_index=True) if pub_list     else pd.DataFrame()
df_pats    = pd.concat(pat_list,     ignore_index=True) if pat_list     else pd.DataFrame()
df_grants  = pd.concat(grant_list,   ignore_index=True) if grant_list   else pd.DataFrame()
df_consult = pd.concat(consult_list, ignore_index=True) if consult_list else pd.DataFrame()
df_grants_all = merge_grants_and_consult(df_grants, df_consult)

YEAR_COL = get_col(df_pubs, ["publication year", "year"])
CAT_COL  = get_col(df_pubs, ["publication category", "category"])
STAT_COL = get_col(df_pubs, ["status"])
QCOL     = get_col(df_pubs, ["quartile"])

if YEAR_COL and not df_pubs.empty:
    df_pubs[YEAR_COL] = pd.to_numeric(df_pubs[YEAR_COL], errors="coerce")
    f_pubs = df_pubs[(df_pubs[YEAR_COL] >= 2022) & df_pubs[CAT_COL].astype(str).str.contains("Journal|Conference", case=False, na=False)].copy()
else:
    f_pubs = pd.DataFrame()

# ── KPI CALCULATION FIX ──
def compute_unique_grant_total(grant_df, consult_df):
    unique_projects = []
    for df in [grant_df, consult_df]:
        if df.empty: continue
        amt_col = get_col(df, ["grant amount", "amount"])
        title_col = get_col(df, ["title"])
        if amt_col and title_col:
            for _, row in df.iterrows():
                amt = clean_currency(row[amt_col])
                # Deduplicate by normalizing the title
                t_norm = re.sub(r'[^a-z0-9]', '', str(row[title_col]).lower())
                if t_norm:
                    unique_projects.append({"t": t_norm, "a": amt})
    if not unique_projects: return 0.0
    return pd.DataFrame(unique_projects).drop_duplicates(subset=["t", "a"])["a"].sum()

total_grant_amount = compute_unique_grant_total(df_grants, df_consult)

# ──────────────────────────────────────────────
#   SIDEBAR
# ──────────────────────────────────────────────

st.sidebar.title("📡 ECE Department\nPDEU")
view = st.sidebar.radio("🗂️ Navigate", ["📊 Overall Dashboard", "👤 Individual Profile"])

# ──────────────────────────────────────────────
#   OVERALL DASHBOARD
# ──────────────────────────────────────────────

if view == "📊 Overall Dashboard":
    st.title("📊 ECE Department — Faculty Dashboard")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("📄 Publications (22+)", len(f_pubs))
    k2.metric("🔬 Patents (22+)",     len(df_pats))
    k3.metric("🏦 Unique Grants",     len(df_grants_all.drop_duplicates(subset=[get_col(df_grants_all, ['title'])])) if not df_grants_all.empty else 0)
    k4.metric("💰 Total Grant Amount", fmt_inr(total_grant_amount))
    k5.metric("👩‍🏫 Faculty Members",   len(all_fac))

    st.divider()
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("📈 Publication Trend")
        if not f_pubs.empty and YEAR_COL:
            trend = f_pubs.groupby(YEAR_COL).size().reset_index(name="Count")
            st.plotly_chart(px.line(trend, x=YEAR_COL, y="Count", markers=True), use_container_width=True)

    with c2:
        st.subheader("📊 Journal vs Conference Split")
        if not f_pubs.empty and CAT_COL:
            pie_df = safe_vc(f_pubs[CAT_COL].astype(str).str.title(), label="Type")
            st.plotly_chart(px.pie(pie_df, names="Type", values="Count", hole=0.45), use_container_width=True)

    st.divider()
    st.subheader("💰 Grant & Consultancy Amount by Faculty")
    rows = []
    for fac in all_fac:
        fac_total = 0
        for df in [df_grants, df_consult]:
            if df.empty: continue
            fac_df = df[df["Faculty"] == fac]
            ac = get_col(fac_df, ["amount"])
            if ac: fac_total += fac_df[ac].apply(clean_currency).sum()
        rows.append({"Faculty": fac, "Amount": fac_total})

    grant_by_fac = pd.DataFrame(rows).sort_values("Amount", ascending=False).query("Amount > 0")
    if not grant_by_fac.empty:
        fig = px.bar(grant_by_fac, x="Faculty", y="Amount", text=grant_by_fac["Amount"].apply(fmt_inr))
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("🏆 Faculty Productivity")
    p_cnt = f_pubs["Faculty"].value_counts() if not f_pubs.empty else pd.Series()
    pt_cnt = df_pats["Faculty"].value_counts() if not df_pats.empty else pd.Series()
    g_cnt = df_grants_all["Faculty"].value_counts() if not df_grants_all.empty else pd.Series()
    prod = pd.DataFrame({"Papers": p_cnt, "Patents": pt_cnt, "Grants": g_cnt}).fillna(0).astype(int)
    prod = prod.reindex(all_fac, fill_value=0).sort_values("Papers", ascending=False).reset_index().rename(columns={"index": "Faculty"})
    st.plotly_chart(px.bar(prod, x="Faculty", y=["Papers", "Patents", "Grants"], barmode="stack"), use_container_width=True)

    st.divider()
    st.subheader("🔥 Faculty × Year Heatmap")
    if not f_pubs.empty and YEAR_COL:
        heat = f_pubs.groupby(["Faculty", YEAR_COL]).size().unstack(fill_value=0).reindex(all_fac, fill_value=0)
        st.plotly_chart(px.imshow(heat, text_auto=True, color_continuous_scale="Blues", aspect="auto"), use_container_width=True)

    st.divider()
    st.subheader("🥇 Quartile Analysis (2022+ Journals)")
    if not f_pubs.empty and QCOL:
        q_df = f_pubs[f_pubs[CAT_COL].astype(str).str.contains("Journal", case=False, na=False)].copy()
        q_df[QCOL] = q_df[QCOL].astype(str).str.strip().str.upper()
        q_final = pd.DataFrame({"Quartile": ["Q1", "Q2", "Q3", "Q4"], "Count": [len(q_df[q_df[QCOL]==q]) for q in ["Q1", "Q2", "Q3", "Q4"]]})
        st.plotly_chart(px.bar(q_final, x="Quartile", y="Count", color="Quartile", text="Count"), use_container_width=True)

# ──────────────────────────────────────────────
#   INDIVIDUAL PROFILE
# ──────────────────────────────────────────────

else:
    fac = st.sidebar.selectbox("Select Faculty Member", all_fac)
    tabs = data_dict[fac]
    df_p = tabs["pub"]
    
    fac_grant_total = 0
    for k in ["grant", "consult"]:
        sec = tabs[k]
        ac = get_col(sec, ["amount"])
        if ac: fac_grant_total += sec[ac].apply(clean_currency).sum()

    st.title(f"👤 {fac}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📄 Total (J+C)", len(df_p))
    m2.metric("🔬 Patents",     len(tabs["patent"]))
    m3.metric("🏦 Funded Items", len(tabs["grant"]) + len(tabs["consult"]))
    m4.metric("💰 Grant Amount", fmt_inr(fac_grant_total))

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📈 Publications per Year")
        yc = get_col(df_p, ["year"])
        if yc:
            y_data = df_p.groupby(yc).size().reset_index(name="Count")
            st.plotly_chart(px.bar(y_data, x=yc, y="Count", text="Count"), use_container_width=True)
    with c2:
        st.subheader("📊 Category Split")
        cc = get_col(df_p, ["category"])
        if cc:
            st.plotly_chart(px.pie(df_p, names=cc, hole=0.4), use_container_width=True)

    st.divider()
    s1, s2 = st.columns(2)
    with s1:
        st.subheader("🔬 Patents")
        pt = tabs["patent"]
        if not pt.empty:
            t_col, c_col, y_col = get_col(pt, ["title"]), get_col(pt, ["category"]), get_col(pt, ["year"])
            for _, r in pt.iterrows(): st.markdown(f"**{r[t_col]}** \n*{r[c_col]} · {r[y_col]}*")
    with s2:
        st.subheader("🎖️ Awards & Achievements")
        aw = tabs["award"]
        if not aw.empty:
            d_col = get_col(aw, ["detail", "award"])
            for _, r in aw.iterrows(): st.markdown(f"• **{r[d_col]}**")

    st.divider()
    w1, w2 = st.columns(2)
    with w1:
        st.subheader("🏫 Workshops Organised")
        ws = tabs["workshop"]
        if not ws.empty:
            t_col = get_col(ws, ["title"])
            for _, r in ws.iterrows(): st.markdown(f"• **{r[t_col]}**")
    with w2:
        st.subheader("🏦 Grants & Consultancy")
        for label, key in [("📁 Projects", "grant"), ("🏭 Industry", "consult")]:
            sec = tabs[key]
            if not sec.empty:
                st.markdown(f"**{label}**")
                tc, ac = get_col(sec, ["title"]), get_col(sec, ["amount"])
                for _, r in sec.iterrows(): 
                    st.markdown(f"• {r[tc]} ({fmt_inr(clean_currency(r[ac]))})")

    with st.expander("🎓 Student Achievements"):
        sa = tabs["stud_ach"]
        if not sa.empty:
            ach_c = get_col(sa, ["achievement", "name"])
            for _, r in sa.iterrows(): st.write(f"• {r[ach_c]}")
