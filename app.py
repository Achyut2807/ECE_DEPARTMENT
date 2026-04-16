import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(layout="wide", page_title="ECE Faculty Dashboard")

# --- DATA EXTRACTION HELPERS ---

def get_col_name(df, keywords):
    """Finds a column name based on keywords (case-insensitive)."""
    for c in df.columns:
        if any(k.lower() in str(c).lower() for k in keywords):
            return c
    return None

def clean_dataframe(df):
    """Removes empty rows and standardizes column names to strings."""
    if df.empty: return df
    df = df.dropna(how='all').reset_index(drop=True)
    df.columns = [str(c).strip() for c in df.columns]
    # Deduplicate column names to prevent Concat errors
    cols = pd.Series(df.columns)
    for dup in cols[cols.duplicated()].unique(): 
        cols[cols[cols == dup].index] = [
            f"{dup}_{i}" if i != 0 else dup for i in range(len(cols[cols == dup]))
        ]
    df.columns = cols
    return df

@st.cache_data
def load_and_parse_data(file_path):
    all_sheets = pd.read_excel(file_path, sheet_name=None, header=None)
    parsed_data = {}
    excluded = ['Sheet1', 'Sheet 1', 'Sheet2', 'Master', 'Summary']
    
    for name, df in all_sheets.items():
        if name in excluded or "Sheet" in name: continue
        
        df_str = df.astype(str)
        def find_row(keyword):
            mask = df_str.apply(lambda x: x.str.contains(keyword, case=False, na=False)).any(axis=1)
            return int(df[mask].index[0]) if mask.any() else None

        sections = {
            "pub": find_row("Publication Details"),
            "patent": find_row("Patent/Copyright Detail"),
            "grant": find_row("Project"),
            "workshop": find_row("Workshop/Seminar/Conference Organised"),
            "stud_ach": find_row("Student Acheivements"),
            "award": find_row("Award Recived")
        }
        
        indices = sorted([idx for idx in sections.values() if idx is not None])
        indices.append(len(df))

        def extract_table(key):
            start = sections[key]
            if start is None: return pd.DataFrame()
            end = next((i for i in indices if i > start), len(df))
            
            sub = df.iloc[start+1 : end].reset_index(drop=True)
            # Find the actual header row (usually the first row with text)
            header_idx = 0
            for i in range(len(sub)):
                if sub.iloc[i].dropna().shape[0] > 1:
                    header_idx = i
                    break
            
            sub.columns = sub.iloc[header_idx]
            sub = sub[header_idx + 1:].dropna(how='all')
            return clean_dataframe(sub)

        parsed_data[name] = {k: extract_table(k) for k in sections.keys()}
    
    return parsed_data

# --- LOAD DATA ---
try:
    data_dict = load_and_parse_data("Protected_Deparment_FactSheet-2.xlsx")
except Exception as e:
    st.error(f"Error reading file: {e}")
    st.stop()

# --- PRE-PROCESS DATA ---
all_fac_list = sorted(list(data_dict.keys()))
all_pubs_l, all_pats_l, all_grants_l = [], [], []

for fac, tables in data_dict.items():
    p, pt, g = tables['pub'].copy(), tables['patent'].copy(), tables['grant'].copy()
    if not p.empty: p['Faculty'] = fac; all_pubs_l.append(p)
    if not pt.empty: pt['Faculty'] = fac; all_pats_l.append(pt)
    if not g.empty: g['Faculty'] = fac; all_grants_l.append(g)

df_all_p = pd.concat(all_pubs_l, ignore_index=True) if all_pubs_l else pd.DataFrame()
df_all_pt = pd.concat(all_pats_l, ignore_index=True) if all_pats_l else pd.DataFrame()
df_all_g = pd.concat(all_grants_l, ignore_index=True) if all_grants_l else pd.DataFrame()

# Global Filtering (2022+ and core categories)
y_col_p = get_col_name(df_all_p, ['year'])
cat_col_p = get_col_name(df_all_p, ['category'])

if y_col_p and not df_all_p.empty:
    df_all_p[y_col_p] = pd.to_numeric(df_all_p[y_col_p], errors='coerce')
    f_pubs = df_all_p[(df_all_p[y_col_p] >= 2022)].copy()
    if cat_col_p:
        f_pubs = f_pubs[f_pubs[cat_col_p].astype(str).str.contains("Journal|Conference", case=False, na=False)]
else:
    f_pubs = pd.DataFrame()

y_col_pt = get_col_name(df_all_pt, ['year'])
if y_col_pt and not df_all_pt.empty:
    df_all_pt[y_col_pt] = pd.to_numeric(df_all_pt[y_col_pt], errors='coerce')
    f_pats = df_all_pt[df_all_pt[y_col_pt] >= 2022].copy()
else:
    f_pats = pd.DataFrame()

# --- SIDEBAR ---
view = st.sidebar.radio("Navigation", ["Overall Dashboard", "Individual Profile"])

# --- OVERALL DASHBOARD ---
if view == "Overall Dashboard":
    st.title("📊 Department Dashboard (2022 - Present)")
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Records (J+C+P)", len(f_pubs) + len(f_pats))
    k2.metric("Total Faculties", len(all_fac_list))
    k3.metric("Total Grants/Funding", len(df_all_g))

    st.divider()

    # Trend and Category Pie
    c_trend, c_pie = st.columns(2)
    with c_trend:
        st.subheader("📈 Publication Trend")
        if not f_pubs.empty:
            trend = f_pubs.groupby(y_col_p).size().reset_index(name='Count')
            st.plotly_chart(px.line(trend, x=y_col_p, y='Count', markers=True), use_container_width=True)
    with c_pie:
        st.subheader("📊 Journal vs Conference")
        if not f_pubs.empty:
            pie_df = f_pubs[cat_col_p].astype(str).str.capitalize().value_counts().reset_index()
            pie_df.columns = ['Type', 'Count']
            st.plotly_chart(px.pie(pie_df, names='Type', values='Count', hole=0.4), use_container_width=True)

    # Faculty Productivity
    st.subheader("🏆 Faculty Productivity (All 28 Members)")
    p_cnt = f_pubs['Faculty'].value_counts()
    pt_cnt = f_pats['Faculty'].value_counts()
    prod = pd.DataFrame({'Papers': p_cnt, 'Patents': pt_cnt}).fillna(0)
    prod['Total'] = prod['Papers'] + prod['Patents']
    prod = prod.reindex(all_fac_list, fill_value=0).sort_values('Total', ascending=False).reset_index().rename(columns={'index':'Faculty'})
    
    st.plotly_chart(px.bar(prod, x='Faculty', y=['Papers', 'Patents'], barmode='stack', height=500), use_container_width=True)

    # Heatmap
    st.subheader("🔥 Faculty Publication Heatmap")
    if not f_pubs.empty:
        heat = f_pubs.groupby(['Faculty', y_col_p]).size().unstack(fill_value=0)
        heat = heat.reindex(all_fac_list, fill_value=0)
        st.plotly_chart(px.imshow(heat, text_auto=True, aspect="auto", color_continuous_scale="RdBu_r"), use_container_width=True)

# --- INDIVIDUAL PROFILE ---
else:
    fac = st.sidebar.selectbox("Select Faculty", all_fac_list)
    tabs = data_dict[fac]
    df_p = tabs['pub']
    
    st.title(f"👤 Faculty Profile: {fac}")

    if not df_p.empty:
        # Dynamic Column Discovery
        yc = get_col_name(df_p, ['year'])
        cc = get_col_name(df_p, ['category'])
        sc = get_col_name(df_p, ['status'])
        qc = get_col_name(df_p, ['quartile'])
        tc = get_col_name(df_p, ['title'])

        df_p[yc] = pd.to_numeric(df_p[yc], errors='coerce')
        # Only show core categories in charts
        mask = df_p[cc].astype(str).str.contains("Journal|Conference", case=False, na=False)
        df_clean = df_p[mask].copy()

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📈 Publications per Year")
            y_data = df_clean.groupby(yc).size().reset_index(name='Count')
            st.plotly_chart(px.bar(y_data, x=yc, y='Count'), use_container_width=True)
            
        with col2:
            st.subheader("📊 Category Distribution")
            p_c = len(df_clean[df_clean[cc].astype(str).str.contains("Journal", case=False, na=False)])
            c_c = len(df_clean[df_clean[cc].astype(str).str.contains("Conference", case=False, na=False)])
            pat_c = len(tabs['patent'])
            pie_v = pd.DataFrame({'Cat':['Journal','Conference','Patent'], 'Val':[p_c, c_c, pat_c]})
            st.plotly_chart(px.pie(pie_v, names='Cat', values='Val', hole=0.4), use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            st.subheader("📌 Status Analysis")
            if sc:
                # Clean Status: Filter out "None", empty strings, or numbers
                s_df = df_clean.copy()
                s_df[sc] = s_df[sc].astype(str).str.strip().str.capitalize()
                s_df = s_df[s_df[sc].str.contains("Published|Accepted|Submi", case=False, na=False)]
                if not s_df.empty:
                    st.plotly_chart(px.bar(s_df[sc].value_counts().reset_index(), x='index', y=sc, labels={'index':'Status'}), use_container_width=True)
                else: st.info("No status data (Accepted/Published/Submitted) found.")
            else: st.warning("Status column not detected.")

        with col4:
            st.subheader("🏆 Quartile Analysis")
            if qc:
                # Clean Quartile: Only show Q1-Q4
                q_df = df_clean.copy()
                q_df[qc] = q_df[qc].astype(str).str.strip().str.upper()
                q_order = ['Q1', 'Q2', 'Q3', 'Q4']
                q_counts = q_df[qc].value_counts()
                q_final = pd.DataFrame({'Quartile': q_order, 'Count': [q_counts.get(q, 0) for q in q_order]})
                st.plotly_chart(px.bar(q_final, x='Quartile', y='Count', color='Quartile'), use_container_width=True)
            else: st.warning("Quartile column not detected.")

    st.divider()
    s1, s2 = st.columns(2)
    with s1:
        st.subheader("🎖️ Achievements / Awards")
        for _, r in tabs['award'].iterrows(): st.markdown(f"• {next((v for v in r if len(str(v))>5), 'Award')}")
        for _, r in tabs['stud_ach'].iterrows(): st.markdown(f"• (Student) {next((v for v in r if len(str(v))>5), 'Achievement')}")
    with s2:
        st.subheader("📜 Patents")
        pt_df = tabs['patent']
        if not pt_df.empty:
            pt_tit = get_col_name(pt_df, ['title'])
            pt_typ = get_col_name(pt_df, ['category', 'type'])
            for _, r in pt_df.iterrows(): st.markdown(f"**{r[pt_tit]}** \n*Type: {r[pt_typ]}*")
    
    st.subheader("🏫 Workshops / Seminars")
    ws_df = tabs['workshop']
    if not ws_df.empty:
        ws_t = get_col_name(ws_df, ['title'])
        for _, r in ws_df.iterrows(): st.markdown(f"• {r[ws_t]}")
