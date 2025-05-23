import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import io

# ─── Page Configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EduAid - Empowering Education Inc.",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 EduAid: College Financial Aid Navigator")
st.markdown("""
Welcome to **EduAid**, brought to you by **Empowering Education Inc.**!  
Explore financial aid options, compare colleges, read student reviews, plan visits, and dive into transfer insights.
""")

# ─── Data Loading & Validation ─────────────────────────────────────────────────
@st.cache_data(ttl=24*3600, show_spinner=False)
def load_scorecard_data(path="college_scorecard_data.csv"):
    try:
        df = pd.read_csv(path)
        if df.empty:
            raise ValueError("Data file is empty")
        return df
    except Exception as e:
        st.error(f"Failed to load college data: {e}")
        st.stop()

df = load_scorecard_data()

# ─── Caching External Data Sources ─────────────────────────────────────────────
@st.cache_data(ttl=6*3600)
def load_unigo_comments(school_slug: str) -> pd.DataFrame:
    """Scrape Unigo reviews by slug (e.g. 'harvard-university')."""
    url = f"https://www.unigo.com/college/{school_slug}/reviews"
    res = requests.get(url, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")
    reviews = []
    for card in soup.select(".ReviewCard"):
        try:
            reviews.append({
                "author": card.select_one(".ReviewerName").text.strip(),
                "rating": float(card.select_one(".StarRating")["data-rating"]),
                "text": card.select_one(".ReviewText").text.strip()
            })
        except:
            continue
    return pd.DataFrame(reviews)

@st.cache_data(ttl=6*3600)
def load_collegewise_comments(school_name: str) -> pd.DataFrame:
    url = f"https://collegewise.com/schools/{school_name.replace(' ', '-').lower()}/reviews"
    res = requests.get(url, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")
    reviews = []
    for card in soup.select(".review-card"):
        try:
            reviews.append({
                "author": card.select_one(".review-author").text.strip(),
                "rating": float(card.select_one(".review-stars")["data-rating"]),
                "text": card.select_one(".review-text").text.strip()
            })
        except:
            continue
    return pd.DataFrame(reviews)

@st.cache_data(ttl=24*3600)
def load_tour_events(school_url: str) -> pd.DataFrame:
    res = requests.get(school_url.rstrip("/") + "/visit/events", timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")
    events = []
    for item in soup.select(".event-item"):
        try:
            events.append({
                "name": item.select_one(".event-title").text.strip(),
                "date": item.select_one(".event-date").text.strip(),
                "latitude": float(item["data-lat"]),
                "longitude": float(item["data-lng"])
            })
        except:
            continue
    return pd.DataFrame(events)

# ─── Sidebar Navigation ───────────────────────────────────────────────────────
st.sidebar.header("🔍 Select a Task")
task = st.sidebar.selectbox(
    "What would you like to do?",
    [
        "Find Net Price Calculator",
        "Research School Financial Aid",
        "Compare Schools",
        "Contact Financial Aid Office",
        "Scholarship Search",
        "Student Reviews & Insights",
        "Transfer Admissions Dashboard",
        "Campus Visit Planner",
    ]
)
st.sidebar.markdown("---")
st.sidebar.markdown("""
#### Built with 💙 by  
### Empowering Education Inc.  
[Visit our website](https://www.empoweringeducationfund.org/)
""")

# ─── Task 1: Net Price Calculator ──────────────────────────────────────────────
if task == "Find Net Price Calculator":
    st.header("🔗 Find a Net Price Calculator")
    school = st.selectbox("Search and select a school", df['school_name'].unique())
    if school:
        row = df[df.school_name == school].iloc[0]
        url = row.get('price_calculator_url', '')
        if url and not url.startswith(('http://','https://')):
            url = 'https://' + url
        if url:
            st.success(f"✅ Visit the Net Price Calculator for **{school}**:")
            st.markdown(f"[📄 Net Price Calculator]({url})", unsafe_allow_html=True)
        else:
            st.info(f"No Net Price Calculator link available for **{school}**.")

# ─── Task 2: Financial Aid Research ────────────────────────────────────────────
elif task == "Research School Financial Aid":
    st.header("💡 School Financial Aid Information")
    school = st.selectbox("Search and select a school", df['school_name'].unique())
    if school:
        data = df[df.school_name == school]
        if data.empty:
            st.error("Data not found."); st.stop()
        s = data.iloc[0]
        col1, col2 = st.columns(2)
        def show_metric(col, label, key, pct=False, curr=False):
            val = s.get(key, np.nan)
            if pd.isna(val):
                col.info(f"{label}: N/A")
            else:
                fmt = f"${val:,.0f}" if curr else (f"{val*100:.1f}%" if pct else f"{val:.0f}")
                col.metric(label, fmt)
        show_metric(col1, "In-State Tuition", 'in_state_tuition', curr=True)
        show_metric(col2, "Out-of-State Tuition", 'out_of_state_tuition', curr=True)
        show_metric(col1, "Median Debt", 'median_debt', curr=True)
        show_metric(col2, "Completion Rate", 'completion_rate', pct=True)
        show_metric(col1, "Admission Rate", 'admission_rate', pct=True)
        show_metric(col2, "Average SAT Score", 'sat_average')

# ─── Task 3: Compare Schools ───────────────────────────────────────────────────
elif task == "Compare Schools":
    st.header("🔄 Compare Schools")
    st.markdown("*Data source: College Scorecard (Last updated: October 2024)*")
    with st.expander("ℹ️ How to use"):
        st.markdown("""
1. Select up to 5 schools  
2. Choose metrics  
3. View & download results  
""")
    available_metrics = {
        "Cost": {'in_state_tuition':'In-State Tuition','out_of_state_tuition':'Out-of-State Tuition','attendance_cost':'Cost of Attendance'},
        "Academics": {'completion_rate':'Graduation Rate','admission_rate':'Admission Rate','sat_average':'SAT Avg'},
        "Diversity": {'percent_white':'% White','percent_black':'% Black','percent_hispanic':'% Hispanic','percent_asian':'% Asian'},
        "Outcomes": {'median_earnings_10yrs':'Median Earnings 10yr'}
    }
    sel = st.multiselect("Select schools (max 5)", df['school_name'].unique(), max_selections=5)
    if sel:
        cat = st.selectbox("Metric category", list(available_metrics.keys()))
        mets = [m for m in available_metrics[cat] if st.checkbox(available_metrics[cat][m], key=m)]
        if mets:
            comp = df[df.school_name.isin(sel)][['school_name']+mets].copy()
            def fmt(v,k):
                if pd.isna(v): return "N/A"
                if 'tuition' in k or 'earnings' in k or 'cost' in k: return f"${v:,.0f}"
                return f"{v*100:.1f}%"
            for m in mets:
                comp[m] = comp[m].apply(lambda x: fmt(x,m))
            comp.columns = ["School"] + [available_metrics[cat][m] for m in mets]
            st.dataframe(comp, use_container_width=True)
            num = df[df.school_name.isin(sel)]
            for m in mets:
                fig = px.bar(num, x='school_name', y=m, title=available_metrics[cat][m])
                st.plotly_chart(fig, use_container_width=True)
            st.subheader("Download")
            fmt_opt = st.radio("Format", ["CSV","Excel"], horizontal=True)
            if fmt_opt == "CSV":
                csv = comp.to_csv(index=False).encode()
                st.download_button("Download CSV", data=csv, file_name=f"compare_{datetime.now():%Y%m%d}.csv", mime="text/csv")
            else:
                buf = io.BytesIO()
                with pd.ExcelWriter(buf) as writer:
                    comp.to_excel(writer, index=False)
                st.download_button("Download Excel", data=buf.getvalue(), file_name=f"compare_{datetime.now():%Y%m%d}.xlsx")

# ─── Task 4: Contact Financial Aid ─────────────────────────────────────────────
elif task == "Contact Financial Aid Office":
    st.header("📞 Contact Financial Aid Office")
    q = st.text_input("Search by name")
    filtered = df[df.school_name.str.contains(q, case=False, na=False)] if q else df
    if filtered.empty:
        st.warning("No matches.")
    school = st.selectbox("Select School", filtered['school_name'].unique())
    if school:
        url = filtered[filtered.school_name==school].iloc[0].get('school_url','')
        if url and not url.startswith(('http://','https://')):
            url = 'https://' + url
        if url:
            st.info(f"Visit financial aid page for **{school}**:")
            st.markdown(f"[🌐 {url}]({url})", unsafe_allow_html=True)
        else:
            st.info("No URL available.")

# ─── Task 5: Scholarship Search ───────────────────────────────────────────────
elif task == "Scholarship Search":
    st.header("💰 Scholarship Resources")
    with st.expander("Types of Aid"):
        st.markdown("""
- **Federal**: Grants, Work-Study, Loans  
- **State**: Local programs  
- **Institutional**: Merit & Need-based  
- **Private**: Organization-sponsored  
""")
    with st.expander("📝 FAFSA"):
        st.markdown("""
- Opens Oct 1; federal deadline Jun 30  
- Apply online: https://studentaid.gov  
""")
    st.markdown("""
**Popular Tools:**  
- [FastWeb](https://www.fastweb.com)  
- [Scholarships.com](https://www.scholarships.com)  
- [College Board](https://bigfuture.collegeboard.org)  
- [Niche](https://www.niche.com/colleges/scholarships/)  
""")
    with st.expander("Deadlines & Tips"):
        st.markdown("""
- Apply early; some aid is first-come  
- Check school-specific deadlines  
- Keep copies of all forms  
""")

# ─── Task 6: Student Reviews & Insights ───────────────────────────────────────
elif task == "Student Reviews & Insights":
    st.header("🗣️ Student Reviews & Insights")
    school = st.selectbox("Select a school", df['school_name'].unique())
    if school:
        slug = df.loc[df.school_name == school, 'unigo_slug'].iloc[0]
        u = load_unigo_comments(slug)
        c = load_collegewise_comments(school)
        combined = pd.concat([u, c], ignore_index=True)
        if combined.empty:
            st.info("No reviews available.")
        else:
            st.subheader("Recent Reviews")
            for _, r in combined.head(10).iterrows():
                st.markdown(f"**{r['author']}** rated **{r['rating']}⭐**")
                st.write(r['text'])
            st.metric("Average Rating", f"{combined['rating'].mean():.1f}⭐")

# ─── Task 7: Transfer Admissions Dashboard ────────────────────────────────────
elif task == "Transfer Admissions Dashboard":
    st.header("🔄 Transfer Admissions Insights")
    school = st.selectbox("Select a school", df['school_name'].unique())
    if school:
        d = df[df.school_name==school].iloc[0]
        col1, col2 = st.columns(2)
        col1.metric("Transfer Admit Rate", f"{d.get('transfer_admit_rate',np.nan)*100:.1f}%")
        col2.metric("Avg. Credits Accepted", f"{d.get('transfer_credit_acceptance',np.nan):.0f}")
        st.markdown("#### Articulation Agreements")
        st.write(d.get("articulation_partners","No data"))

# ─── Task 8: Campus Visit Planner ─────────────────────────────────────────────
elif task == "Campus Visit Planner":
    st.header("🏫 Campus Visit Planner")
    school = st.selectbox("Select a school", df['school_name'].unique())
    if school:
        url = df[df.school_name==school]['school_url'].iloc[0]
        events = load_tour_events(url)
        if events.empty:
            st.info("No upcoming events found.")
        else:
            st.map(events[["latitude","longitude"]])
            st.table(events[["name","date"]])

# ─── Sidebar Resources ────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown("### 📚 Helpful Resources")
st.sidebar.markdown("""
- [College Scorecard](https://collegescorecard.ed.gov/)
- [Federal Student Aid](https://studentaid.gov)
- [FAFSA](https://studentaid.gov/h/apply-for-aid/fafsa)
""")
