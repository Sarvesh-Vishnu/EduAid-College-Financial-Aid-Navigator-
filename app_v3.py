import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import io
import re

# ─── Data Loading & Preprocessing ──────────────────────────────────────────────
@st.cache_data(ttl=24*3600)
def load_and_preprocess_data(path="college_scorecard_data.csv"):
    try:
        df = pd.read_csv(path)
        
        # Normalize column names
        df.columns = (
            df.columns
            .str.strip()
            .str.lower()
            .str.replace(r'[^\w]', '_', regex=True)  # Replace special chars with underscores
            .str.replace(r'_+', '_', regex=True)      # Replace multiple underscores with single
        )
        
        # Rename critical columns
        column_mapping = {
            'unitid': 'unit_id',
            'price_calculator_url': 'net_price_calculator_url',
            'median_earnings_10yrs': 'median_earnings_10yr'
        }
        df.rename(columns=column_mapping, inplace=True)
        
        if df.empty:
            raise ValueError("Data file is empty")
            
        return df
        
    except Exception as e:
        st.error(f"Data loading failed: {str(e)}")
        st.stop()

df = load_and_preprocess_data()

# ─── Caching & Data Fetching ───────────────────────────────────────────────────
@st.cache_data(ttl=6*3600)
def fetch_unigo_reviews(school_id):
    try:
        url = f"https://www.unigo.com/college/{school_id}/reviews"
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        
        reviews = []
        for card in soup.select(".ReviewCard"):
            review_data = {
                "author": card.select_one(".ReviewerName").text.strip() if card.select_one(".ReviewerName") else "Anonymous",
                "rating": float(card.select_one(".StarRating")["data-rating"]) if card.select_one(".StarRating") else 0,
                "text": card.select_one(".ReviewText").text.strip() if card.select_one(".ReviewText") else ""
            }
            reviews.append(review_data)
            
        return pd.DataFrame(reviews)
    
    except Exception as e:
        st.error(f"Failed to fetch Unigo reviews: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=6*3600)
def fetch_collegewise_reviews(school_name):
    try:
        formatted_name = re.sub(r'\W+', '-', school_name.lower())
        url = f"https://collegewise.com/schools/{formatted_name}/reviews"
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        
        reviews = []
        for card in soup.select(".review-card"):
            review_data = {
                "author": card.select_one(".review-author").text.strip() if card.select_one(".review-author") else "Anonymous",
                "rating": float(card.select_one(".review-stars")["data-rating"]) if card.select_one(".review-stars") else 0,
                "text": card.select_one(".review-text").text.strip() if card.select_one(".review-text") else ""
            }
            reviews.append(review_data)
            
        return pd.DataFrame(reviews)
    
    except Exception as e:
        st.error(f"Failed to fetch CollegeWise reviews: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=12*3600)
def fetch_campus_events(school_url):
    try:
        res = requests.get(f"{school_url.rstrip('/')}/visit/events", timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        
        events = []
        for item in soup.select(".event-item"):
            event_data = {
                "name": item.select_one(".event-title").text.strip(),
                "date": item.select_one(".event-date").text.strip(),
                "latitude": float(item["data-lat"]),
                "longitude": float(item["data-lng"])
            }
            events.append(event_data)
            
        return pd.DataFrame(events)
    
    except Exception as e:
        st.error(f"Failed to fetch campus events: {str(e)}")
        return pd.DataFrame()

# ─── UI Configuration ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EduAid - College Financial Navigator",
    page_icon="🎓",
    layout="wide",
    menu_items={
        'Get Help': 'https://www.empoweringeducationfund.org/support',
        'About': "### Empowering Education Inc.\nComprehensive college financial aid analysis tool"
    }
)

st.title("🎓 EduAid: College Financial Aid Navigator")
st.markdown("""
Welcome to **EduAid** - Your comprehensive resource for college financial planning, 
student reviews, and admissions insights. Brought to you by **Empowering Education Inc.**  
""")

# ─── Sidebar Navigation ────────────────────────────────────────────────────────
with st.sidebar:
    st.header("🔍 Navigation")
    task = st.selectbox(
        "Select Feature",
        [
            "Find Net Price Calculator",
            "Research School Financial Aid",
            "Compare Schools",
            "Contact Financial Aid Office",
            "Scholarship Search",
            "Student Reviews & Insights",
            "Transfer Admissions Dashboard",
            "Campus Visit Planner"
        ]
    )
    
    st.markdown("---")
    st.markdown("""
    #### Built with 💙 by  
    ### Empowering Education Inc.  
    [Visit our website](https://www.empoweringeducationfund.org/)
    """)

# ─── Feature Implementations ───────────────────────────────────────────────────
if task == "Find Net Price Calculator":
    st.header("🔗 Net Price Calculator Finder")
    school = st.selectbox("Select School", df['school_name'].unique())
    
    if school:
        school_data = df[df['school_name'] == school].iloc[0]
        url = school_data.get('net_price_calculator_url', '')
        
        if url:
            if not url.startswith(('http://', 'https://')):
                url = f'https://{url}'
            st.success(f"**{school}** Net Price Calculator:")
            st.markdown(f"[📲 Access Calculator]({url})")
        else:
            st.warning("No net price calculator available for this school")

elif task == "Student Reviews & Insights":
    st.header("📚 Student Reviews & Insights")
    school = st.selectbox("Select School", df['school_name'].unique())
    
    if school:
        school_info = df[df['school_name'] == school].iloc[0]
        
        with st.spinner("Gathering student insights..."):
            unigo_df = fetch_unigo_reviews(school_info['unit_id'])
            collegewise_df = fetch_collegewise_reviews(school)
            combined_reviews = pd.concat([unigo_df, collegewise_df], ignore_index=True)
        
        if not combined_reviews.empty:
            st.subheader("Recent Student Reviews")
            for _, review in combined_reviews.head(5).iterrows():
                with st.expander(f"⭐ {review['rating']} - {review['author']}"):
                    st.write(review['text'])
            
            avg_rating = combined_reviews['rating'].mean()
            st.metric("Average Rating", f"{avg_rating:.1f}/5")
        else:
            st.info("No reviews available for this school")

elif task == "Transfer Admissions Dashboard":
    st.header("🔄 Transfer Admissions Insights")
    school = st.selectbox("Select School", df['school_name'].unique())
    
    if school:
        school_data = df[df['school_name'] == school].iloc[0]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Transfer Acceptance Rate", 
                   f"{school_data.get('transfer_admit_rate', 0)*100:.1f}%" if pd.notna(school_data.get('transfer_admit_rate')) else "N/A")
        
        col2.metric("Avg Credits Accepted", 
                   f"{school_data.get('transfer_credit_acceptance', 0):.0f}" if pd.notna(school_data.get('transfer_credit_acceptance')) else "N/A")
        
        col3.metric("Articulation Agreements", 
                   "Available" if school_data.get('articulation_partners') else "None Reported")

elif task == "Campus Visit Planner":
    st.header("🗺️ Campus Visit Planner")
    school = st.selectbox("Select School", df['school_name'].unique())
    
    if school:
        school_data = df[df['school_name'] == school].iloc[0]
        events_df = fetch_campus_events(school_data['school_url'])
        
        if not events_df.empty:
            st.subheader("Upcoming Events")
            st.map(events_df[['latitude', 'longitude']], zoom=12)
            
            with st.expander("Event Details"):
                st.dataframe(events_df[['name', 'date']], hide_index=True)
        else:
            st.info("No upcoming events found for this campus")
