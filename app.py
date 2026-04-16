import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide", page_title="ECE Faculty Dashboard", page_icon="📡")

# ──────────────────────────────────────────────
#  UTILITIES
# ──────────────────────────────────────────────

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
    """
    Extract a table section from a faculty sheet.
    Finds the section header row by start_kw, then the first row with >=3
    non-null values as the column header, reads until end_kw.
    Returns a clean DataFrame. Only keeps rows whose first col is an integer.
    """
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


# ──────────────────────────────────────────────
#  DATA LOADING
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
            "pub":     extract_section(df, "Publication Details",                    "Patent/Copyright Detail"),
            "patent":  extract_section(df, "Patent/Copyright Detail",                "Project"),
            "grant":   extract_section(df, "Project",                                "Industry Consultancy"),
            "consult": extract_section(df, "Industry Consultancy",                   "Workshop/Seminar/Conference Organised"),
            "workshop":extract_section(df, "Workshop/Seminar/Conference Organised",  "Student Acheivements"),
            "stud_ach":extract_section(df, "Student Acheivements",                   "Expert/Invited Talk"),
            "award":   extract_section(df, "Award Recived",                          "Membership"),
        }
    return data


FILE = "Protected_Deparment_FactSheet-2.xlsx"
try:
    data_dict = load_data(FILE)
except FileNotFoundError:
    st.error(f"❌ **{FILE}** not found. Place it in the same folder as this script.")
    st.stop()
except Exception as e:
    st.error(f"❌ Error reading file: {e}")
    st.stop()

# ──────────────────────────────────────────────
#  GLOBAL DATAFRAMES
# ──────────────────────────────────────────────

all_fac = sorted(data_dict.keys())

pub_list, pat_list, grant_list = [], [], []
for fac, tables in data_dict.items():
    for lst, key in [(pub_list, "pub"), (pat_list, "patent"), (grant_list, "grant")]:
        t = tables[key].copy()
        if not t.empty:
            t["Faculty"] = fac
            lst.append(t)

df_pubs   = pd.concat(pub_list,   ignore_index=True) if pub_list   else pd.DataFrame()
df_pats   = pd.concat(pat_list,   ignore_index=True) if pat_list   else pd.DataFrame()
df_grants = pd.concat(grant_list, ignore_index=True) if grant_list else pd.DataFrame()

YEAR_COL  = get_col(df_pubs, ["publication year", "year"])
CAT_COL   = get_col(df_pubs, ["publication category", "category"])
STAT_COL  = get_col(df_pubs, ["status"])
QCOL      = get_col(df_pubs, ["quartile"])
TITLE_COL = get_col(df_pubs, ["publication title", "title"])

if YEAR_COL and not df_pubs.empty:
    df_pubs[YEAR_COL] = pd.to_numeric(df_pubs[YEAR_COL], errors="coerce")

if YEAR_COL and CAT_COL and not df_pubs.empty:
    f_pubs = df_pubs[
        (df_pubs[YEAR_COL] >= 2022) &
        df_pubs[CAT_COL].astype(str).str.contains("Journal|Conference", case=False, na=False)
    ].copy()
else:
    f_pubs = pd.DataFrame()

PAT_YEAR = get_col(df_pats, ["year"])
if PAT_YEAR and not df_pats.empty:
    df_pats[PAT_YEAR] = pd.to_numeric(df_pats[PAT_YEAR], errors="coerce")
    f_pats = df_pats[df_pats[PAT_YEAR] >= 2022].copy()
else:
    f_pats = df_pats.copy()

# ──────────────────────────────────────────────
#  SIDEBAR
# ──────────────────────────────────────────────

st.sidebar.title("📡 ECE Department\nPDEU")
view = st.sidebar.radio("🗂️ Navigate", ["📊 Overall Dashboard", "👤 Individual Profile"])

# ──────────────────────────────────────────────
#  OVERALL DASHBOARD
# ──────────────────────────────────────────────

if view == "📊 Overall Dashboard":
    st.title("📊 ECE Department — Faculty Dashboard (2022 – Present)")
    st.caption("Journals & Conferences only (unless stated) · Source: Protected_Deparment_FactSheet-2.xlsx")

    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("📄 Publications (J+C, 2022+)", len(f_pubs))
    k2.metric("🔬 Patents (2022+)",            len(f_pats))
    k3.metric("🏦 Grants / Projects",          len(df_grants))
    k4.metric("👩‍🏫 Faculty Members",            len(all_fac))

    st.divider()

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("📈 Publication Trend by Year")
        if not f_pubs.empty and YEAR_COL:
            trend = f_pubs.groupby(YEAR_COL).size().reset_index(name="Count")
            fig = px.line(trend, x=YEAR_COL, y="Count", markers=True,
                          color_discrete_sequence=["#2563EB"])
            fig.update_layout(xaxis_title="Year", yaxis_title="Publications")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No trend data.")

    with c2:
        st.subheader("📊 Journal vs Conference Split")
        if not f_pubs.empty and CAT_COL:
            pie_df = safe_vc(f_pubs[CAT_COL].astype(str).str.strip().str.title(), label="Type")
            fig = px.pie(pie_df, names="Type", values="Count", hole=0.45,
                         color_discrete_sequence=px.colors.qualitative.Set2)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No category data.")

    st.divider()

    st.subheader("🏆 Faculty Productivity — All Members")
    p_cnt  = f_pubs["Faculty"].value_counts()    if not f_pubs.empty    else pd.Series(dtype=int)
    pt_cnt = f_pats["Faculty"].value_counts()    if not f_pats.empty    else pd.Series(dtype=int)
    g_cnt  = df_grants["Faculty"].value_counts() if not df_grants.empty else pd.Series(dtype=int)

    prod = pd.DataFrame({"Papers": p_cnt, "Patents": pt_cnt, "Grants": g_cnt}).fillna(0).astype(int)
    prod["Total"] = prod["Papers"] + prod["Patents"] + prod["Grants"]
    prod = (prod.reindex(all_fac, fill_value=0)
                .sort_values("Total", ascending=False)
                .reset_index()
                .rename(columns={"index": "Faculty"}))

    fig = px.bar(prod, x="Faculty", y=["Papers", "Patents", "Grants"],
                 barmode="stack", height=480,
                 color_discrete_map={"Papers": "#2563EB", "Patents": "#16A34A", "Grants": "#D97706"})
    fig.update_layout(xaxis_tickangle=-40, legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("🔥 Faculty × Year Publication Heatmap")
    if not f_pubs.empty and YEAR_COL:
        heat = f_pubs.groupby(["Faculty", YEAR_COL]).size().unstack(fill_value=0)
        heat = heat.reindex(all_fac, fill_value=0)[sorted(heat.columns)]
        fig = px.imshow(heat, text_auto=True, aspect="auto",
                        color_continuous_scale="Blues",
                        labels={"x": "Year", "y": "Faculty", "color": "Papers"})
        fig.update_layout(height=620)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("🥇 Quartile Distribution (Journals, 2022+)")
    if not f_pubs.empty and QCOL and CAT_COL:
        q_df = f_pubs[f_pubs[CAT_COL].astype(str).str.contains("Journal", case=False, na=False)].copy()
        q_df[QCOL] = q_df[QCOL].astype(str).str.strip().str.upper()
        q_order  = ["Q1", "Q2", "Q3", "Q4"]
        q_counts = q_df[QCOL].value_counts()
        q_final  = pd.DataFrame({"Quartile": q_order,
                                  "Count": [int(q_counts.get(q, 0)) for q in q_order]})
        fig = px.bar(q_final, x="Quartile", y="Count", color="Quartile", text="Count",
                     color_discrete_map={"Q1":"#16A34A","Q2":"#2563EB","Q3":"#D97706","Q4":"#DC2626"})
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("📋 Raw Publication Data (2022+, J & C)"):
        if not f_pubs.empty:
            st.dataframe(f_pubs.reset_index(drop=True), use_container_width=True)

# ──────────────────────────────────────────────
#  INDIVIDUAL PROFILE
# ──────────────────────────────────────────────

else:
    fac  = st.sidebar.selectbox("Select Faculty Member", all_fac)
    tabs = data_dict[fac]
    df_p = tabs["pub"].copy()

    st.title(f"👤 {fac}")
    st.caption("Individual research profile — all years shown unless otherwise filtered")

    yc = get_col(df_p, ["publication year", "year"])
    cc = get_col(df_p, ["publication category", "category"])
    sc = get_col(df_p, ["status"])
    qc = get_col(df_p, ["quartile"])
    tc = get_col(df_p, ["publication title", "title"])
    vc_col = get_col(df_p, ["published in", "journal"])

    if yc:
        df_p[yc] = pd.to_numeric(df_p[yc], errors="coerce")

    df_core = df_p[df_p[cc].astype(str).str.contains("Journal|Conference", case=False, na=False)].copy() \
              if cc else df_p.copy()

    journal_count = len(df_core[df_core[cc].astype(str).str.contains("Journal",    case=False, na=False)]) if cc else 0
    conf_count    = len(df_core[df_core[cc].astype(str).str.contains("Conference", case=False, na=False)]) if cc else 0
    patent_count  = len(tabs["patent"])
    grant_count   = len(tabs["grant"])

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("📄 Total (J+C)", journal_count + conf_count)
    m2.metric("📰 Journals",    journal_count)
    m3.metric("🎤 Conferences", conf_count)
    m4.metric("🔬 Patents",     patent_count)
    m5.metric("🏦 Grants",      grant_count)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Publications per Year")
        if yc and not df_core.empty:
            y_data = df_core.groupby(yc).size().reset_index(name="Count")
            fig = px.bar(y_data, x=yc, y="Count", text="Count",
                         color_discrete_sequence=["#2563EB"])
            fig.update_traces(textposition="outside")
            fig.update_layout(xaxis_title="Year", yaxis_title="Count")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No year data.")

    with col2:
        st.subheader("📊 Journal / Conference / Patent")
        pie_v = pd.DataFrame({
            "Type":  ["Journal", "Conference", "Patent"],
            "Count": [journal_count, conf_count, patent_count]
        })
        fig = px.pie(pie_v, names="Type", values="Count", hole=0.42,
                     color_discrete_sequence=["#2563EB", "#16A34A", "#D97706"])
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        st.subheader("📌 Publication Status")
        if sc and not df_core.empty:
            s_df = df_core.copy()
            s_df[sc] = s_df[sc].astype(str).str.strip().str.capitalize()
            s_df = s_df[s_df[sc].str.contains("Published|Accepted|Submitted", case=False, na=False)]
            if not s_df.empty:
                vc_s = safe_vc(s_df[sc], label="Status")
                fig = px.bar(vc_s, x="Status", y="Count", color="Status", text="Count",
                             color_discrete_map={"Published":"#16A34A","Accepted":"#2563EB","Submitted":"#D97706"})
                fig.update_traces(textposition="outside")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No status data (Published / Accepted / Submitted).")
        else:
            st.warning("Status column not detected.")

    with col4:
        st.subheader("🏆 Quartile Analysis (Journals)")
        if qc and cc and not df_core.empty:
            j_only = df_core[df_core[cc].astype(str).str.contains("Journal", case=False, na=False)].copy()
            j_only[qc] = j_only[qc].astype(str).str.strip().str.upper()
            q_order  = ["Q1", "Q2", "Q3", "Q4"]
            q_counts = j_only[qc].value_counts()
            q_final  = pd.DataFrame({"Quartile": q_order,
                                      "Count": [int(q_counts.get(q, 0)) for q in q_order]})
            fig = px.bar(q_final, x="Quartile", y="Count", color="Quartile", text="Count",
                         color_discrete_map={"Q1":"#16A34A","Q2":"#2563EB","Q3":"#D97706","Q4":"#DC2626"})
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Quartile column not detected.")

    with st.expander("📋 Full Publication List"):
        if not df_p.empty:
            display_cols = [c for c in [yc, cc, tc, vc_col, sc, qc] if c]
            st.dataframe(df_p[display_cols].reset_index(drop=True), use_container_width=True)
        else:
            st.info("No publication data.")

    st.divider()
    s1, s2 = st.columns(2)

    with s1:
        st.subheader("🔬 Patents")
        pt_df = tabs["patent"]
        if not pt_df.empty:
            pt_title = get_col(pt_df, ["title"])
            pt_cat   = get_col(pt_df, ["patent category", "category", "type"])
            pt_year  = get_col(pt_df, ["year"])
            for _, r in pt_df.iterrows():
                t_val = str(r[pt_title]).strip() if pt_title else "—"
                c_val = str(r[pt_cat]).strip()   if pt_cat   else "—"
                y_val = str(r[pt_year]).strip()  if pt_year  else "—"
                st.markdown(f"**{t_val}**  \n*{c_val} · {y_val}*")
        else:
            st.info("No patents on record.")

    with s2:
        st.subheader("🎖️ Awards & Achievements")
        award_df = tabs["award"]
        if not award_df.empty:
            det_col  = get_col(award_df, ["detail", "award", "name"])
            cat_col_a = get_col(award_df, ["category"])
            for _, r in award_df.iterrows():
                det = str(r[det_col]).strip()   if det_col   else "—"
                cat_a = str(r[cat_col_a]).strip() if cat_col_a else ""
                suffix = f" _{cat_a}_" if cat_a and cat_a not in ("nan", "") else ""
                st.markdown(f"• **{det}**{suffix}")
        else:
            st.info("No awards on record.")

        stud_df = tabs["stud_ach"]
        if not stud_df.empty:
            st.markdown("**🎓 Student Achievements (under guidance)**")
            ach_col  = get_col(stud_df, ["achievement", "name", "detail"])
            yr_col_s = get_col(stud_df, ["year"])
            for _, r in stud_df.iterrows():
                ach  = str(r[ach_col]).strip()   if ach_col   else "—"
                yr_s = str(r[yr_col_s]).strip()  if yr_col_s  else ""
                suffix = f" *({yr_s})*" if yr_s and yr_s not in ("nan", "") else ""
                st.markdown(f"• {ach}{suffix}")

    st.divider()
    w1, w2 = st.columns(2)

    with w1:
        st.subheader("🏫 Workshops / Seminars Organised")
        ws_df = tabs["workshop"]
        if not ws_df.empty:
            ws_title = get_col(ws_df, ["title"])
            ws_year  = get_col(ws_df, ["year"])
            for _, r in ws_df.iterrows():
                t_val = str(r[ws_title]).strip() if ws_title else "—"
                y_val = str(r[ws_year]).strip()  if ws_year  else ""
                suffix = f" *({y_val})*" if y_val and y_val not in ("nan", "") else ""
                st.markdown(f"• **{t_val}**{suffix}")
        else:
            st.info("No workshops on record.")

    with w2:
        st.subheader("🏦 Grants / Funded Projects")
        gr_df = tabs["grant"]
        if not gr_df.empty:
            gr_title  = get_col(gr_df, ["title"])
            gr_agency = get_col(gr_df, ["funding", "agency"])
            gr_amount = get_col(gr_df, ["amount", "grant amount"])
            gr_year   = get_col(gr_df, ["grant year", "year"])
            for _, r in gr_df.iterrows():
                t_val = str(r[gr_title]).strip()  if gr_title  else "—"
                ag    = str(r[gr_agency]).strip()  if gr_agency else ""
                amt   = str(r[gr_amount]).strip()  if gr_amount else ""
                yr_g  = str(r[gr_year]).strip()    if gr_year   else ""
                meta  = " · ".join(x for x in [ag, amt, yr_g] if x and x != "nan")
                st.markdown(f"• **{t_val}**" + (f"  \n  _{meta}_" if meta else ""))
        else:
            st.info("No grants on record.")
