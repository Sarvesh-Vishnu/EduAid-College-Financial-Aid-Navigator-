import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
from datetime import datetime
import io

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
            .str.replace(r'[^\w]', '_', regex=True)
            .str.replace(r'_+', '_', regex=True)
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


if 'df' not in st.session_state:
    try:
        st.session_state.df = pd.read_csv('college_scorecard_data.csv')
    except FileNotFoundError:
        st.error("Error: Could not find the college data file. Please check the file path.")
        st.stop()

# Data validation
if st.session_state.df.empty:
    st.error("Error: The college data file is empty.")
    st.stop()

# Update the app title and header
st.set_page_config(
    page_title="EduAid - Empowering Education Inc.",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 EduAid: College Financial Aid Navigator")
st.markdown("""
    Welcome to **EduAid**, brought to you by **Empowering Education Inc.**! 
    This tool helps students and families explore financial aid options, compare colleges, 
    and make informed decisions about higher education. 👨‍🎓👩‍🎓
""")

# Sidebar for navigation
st.sidebar.header("🔍 Select a Task")
task = st.sidebar.selectbox(
    "What would you like to do?",
    ("Find Net Price Calculator", 
     "Research School Financial Aid", 
     "Compare Schools",
     "Contact Financial Aid Office",
     "Scholarship Search")
)


st.sidebar.markdown("---")
st.sidebar.markdown("""
    #### Built with 💙 by
    ### Empowering Education Inc.
    [Visit our website](https://www.empoweringeducationfund.org/)
""")



# Task 1: Find Net Price Calculator
if task == "Find Net Price Calculator":
    st.header("🔗 Find a Net Price Calculator for Your Selected School")

    # Combined search and select
    school_name = st.selectbox(
        "🔍 Search and select a school",
        options=st.session_state.df['school_name'].unique(),
        placeholder="Start typing to search...",
        index=None
    )

    if school_name:
        # Get the NPC URL for the selected school
        selected_school = st.session_state.df[st.session_state.df['school_name'] == school_name].iloc[0]
        npc_url = selected_school.get('price_calculator_url', '')

        # Add http:// prefix if the URL doesn't start with http:// or https://
        if npc_url and not npc_url.startswith(('http://', 'https://')):
            npc_url = 'https://' + npc_url

        # Display the NPC link with styling
        if npc_url:
            st.success(f"✅ Visit the Net Price Calculator for **{school_name}**:")
            st.markdown(f"[📄 Net Price Calculator]({npc_url})", unsafe_allow_html=True)
        else:
            st.info(f"No Net Price Calculator link is available for **{school_name}**.")

# Task 2: Research School Financial Aid
elif task == "Research School Financial Aid":
    st.header("💡 Research Financial Aid Information for Selected School")

    try:
        # Combined search and select
        school_name = st.selectbox(
            "🔍 Search and select a school",
            options=st.session_state.df['school_name'].unique(),
            placeholder="Start typing to search...",
            index=None
        )

        if school_name:
            # Get the selected school's information with additional error handling
            school_data = st.session_state.df[st.session_state.df['school_name'] == school_name]
            if school_data.empty:
                st.info("Selected school data not found.")
                st.stop()
                
            selected_school = school_data.iloc[0]

            # Display school financial aid information in columns for better layout
            col1, col2 = st.columns(2)
            
            # Helper function to format metrics with error handling
            def display_metric(col, label, value_key, is_percentage=False, is_currency=False):
                try:
                    value = selected_school[value_key]
                    if pd.isna(value):
                        col.info(f"{label}: Data not available")
                    else:
                        if is_percentage:
                            formatted_value = f"{value*100:.2f}%"
                        elif is_currency:
                            formatted_value = f"${value:,.0f}"
                        else:
                            formatted_value = f"{value:.0f}"
                        col.metric(label=label, value=formatted_value)
                except (KeyError, TypeError):
                    col.info(f"{label}: Data not available")

            # Display metrics with error handling
            display_metric(col1, "In-State Tuition", 'in_state_tuition', is_currency=True)
            display_metric(col2, "Out-of-State Tuition", 'out_of_state_tuition', is_currency=True)
            display_metric(col1, "Median Debt", 'median_debt', is_currency=True)
            display_metric(col2, "Completion Rate", 'completion_rate', is_percentage=True)
            display_metric(col1, "Admission Rate", 'admission_rate', is_percentage=True)
            display_metric(col2, "Average SAT Score", 'sat_average')

    except Exception as e:
        st.error("❌ Financial Aid Information not available. Please try again later.")
        st.exception(e)  # Only show this in development, remove in production

# Task 3: Compare Schools
elif task == "Compare Schools":
    st.header("🔄 Compare Schools")
    
    # Data source information
    st.markdown("""
        *Data source: [College Scorecard](https://collegescorecard.ed.gov/) (Last updated: October 2024)*
    """)
    
    with st.expander("ℹ️ About this comparison tool"):
        st.markdown("""
            This tool helps you compare colleges using official data from the U.S. Department of Education's College Scorecard.
            
            **How to use:**
            1. Search and select up to 5 schools to compare
            2. Choose metrics you're interested in
            3. View the comparison and download the results
            
            **Tips:**
            - Compare similar types of institutions for more meaningful results
            - Look at multiple metrics for a comprehensive view
            - Consider both cost and outcome metrics
        """)

    @st.cache_data(ttl=24*3600)
    def load_college_data():
        try:
            df = pd.read_csv('college_scorecard_data.csv')
            if df.empty:
                st.error("No data found in the college database.")
                st.stop()
            return df
        except Exception as e:
            st.error(f"Error loading college data: {str(e)}")
            st.stop()

    # Metric definitions with tooltips
    available_metrics = {
        "Cost & Financial": {
            'in_state_tuition': {'label': 'In-State Tuition ($)', 'tooltip': 'Annual tuition for state residents'},
            'out_of_state_tuition': {'label': 'Out-of-State Tuition ($)', 'tooltip': 'Annual tuition for non-state residents'},
            'attendance_cost': {'label': 'Total Cost of Attendance ($)', 'tooltip': 'Total annual cost including tuition, room, board, and other expenses'},
            'net_price_public': {'label': 'Net Price - Public ($)', 'tooltip': 'Average annual net price after aid at public institutions'},
            'net_price_private': {'label': 'Net Price - Private ($)', 'tooltip': 'Average annual net price after aid at private institutions'},
            'median_debt': {'label': 'Median Student Debt ($)', 'tooltip': 'Median federal debt of graduates'},
            'pell_grant_rate': {'label': 'Non-Loan Aid Rate (%)', 'tooltip': 'Percentage of financial aid that is not based on loans'},
        },
        "Academic Performance": {
            'completion_rate': {'label': 'Graduation Rate (%)', 'tooltip': 'Percentage of students who graduate within 150% of expected time'},
            'admission_rate': {'label': 'Admission Rate (%)', 'tooltip': 'Percentage of applicants who are admitted'},
            'sat_average': {'label': 'Average SAT Score', 'tooltip': 'Average SAT score of admitted students'},
        },
        "Student Demographics": {
            'student_size': {'label': 'Total Enrollment', 'tooltip': 'Total number of enrolled students'},
            'first_generation': {'label': 'First Generation Students (%)', 'tooltip': 'Percentage of first-generation college students'},
            'age_entry': {'label': 'Average Age at Entry', 'tooltip': 'Average age of students when they first enroll'},
            'median_family_income': {'label': 'Median Family Income ($)', 'tooltip': 'Median family income of students'},
            'percent_white': {'label': 'White Students (%)', 'tooltip': 'Percentage of students who identify as White'},
            'percent_black': {'label': 'Black Students (%)', 'tooltip': 'Percentage of students who identify as Black'},
            'percent_hispanic': {'label': 'Hispanic Students (%)', 'tooltip': 'Percentage of students who identify as Hispanic'},
            'percent_asian': {'label': 'Asian Students (%)', 'tooltip': 'Percentage of students who identify as Asian'},
            'percent_non_white': {'label': 'Non-White Students (%)', 'tooltip': 'Total percentage of non-White students'},
            'locale': {'label': 'Campus Location', 'tooltip': 'Type of area where campus is located (urban, suburban, rural)'},
        },
        "Post-Graduation": {
            'median_earnings_10yrs': {'label': 'Median Earnings after 10 years ($)', 'tooltip': 'Median earnings of graduates 10 years after enrollment'},
        }
    }

    # Initialize session state for selected schools if it doesn't exist
    if 'selected_schools' not in st.session_state:
        st.session_state.selected_schools = []
    
    # Combined search and select with multiselect
    selected_schools = st.multiselect(
        "🔍 Search and select schools to compare (max 5)",
        options=st.session_state.df['school_name'].unique(),
        default=st.session_state.selected_schools,
        max_selections=5,
        placeholder="Start typing to search..."
    )

    # Update session state
    st.session_state.selected_schools = selected_schools

    # Clear selection button
    if st.button("Clear Selection"):
        st.session_state.selected_schools = []
        st.rerun()

    if st.session_state.selected_schools:
        # Metric selection
        st.subheader("📊 Select Comparison Metrics")
        metric_category = st.selectbox(
            "Choose a category of metrics",
            options=list(available_metrics.keys())
        )

        selected_metrics = []
        for metric, info in available_metrics[metric_category].items():
            col1, col2 = st.columns([1, 4])
            if col1.checkbox(info['label'], key=metric):
                selected_metrics.append(metric)
                col2.info(info['tooltip'])

        if selected_metrics:
            # Prepare comparison data
            comparison_df = st.session_state.df[st.session_state.df['school_name'].isin(st.session_state.selected_schools)].copy()

            # Format the data
            def format_value(value, metric):
                if pd.isna(value):
                    return "N/A"
                if metric in ['in_state_tuition', 'out_of_state_tuition', 'attendance_cost', 
                            'net_price_public', 'net_price_private', 'median_debt', 
                            'median_family_income', 'median_earnings_10yrs']:
                    return f"${value:,.0f}"
                elif metric in ['completion_rate', 'admission_rate', 'first_generation', 
                               'pell_grant_rate', 'percent_white', 'percent_black', 
                               'percent_hispanic', 'percent_asian', 'percent_non_white']:
                    return f"{value*100:.1f}%" if value <= 1 else f"{value:.1f}%"
                elif metric in ['student_size', 'sat_average']:
                    return f"{int(value):,}"
                elif metric == 'age_entry':
                    return f"{value:.1f} years"
                elif metric == 'locale':
                    locale_map = {
                        11: 'City: Large', 12: 'City: Midsize', 13: 'City: Small',
                        21: 'Suburb: Large', 22: 'Suburb: Midsize', 23: 'Suburb: Small',
                        31: 'Town: Fringe', 32: 'Town: Distant', 33: 'Town: Remote',
                        41: 'Rural: Fringe', 42: 'Rural: Distant', 43: 'Rural: Remote'
                    }
                    return locale_map.get(value, 'Unknown')
                return str(value)

            for metric in selected_metrics:
                comparison_df[metric] = comparison_df[metric].apply(
                    lambda x: format_value(x, metric)
                )

            # Display comparison table
            st.subheader("📊 Comparison Table")
            display_df = comparison_df[['school_name'] + selected_metrics].copy()
            display_df.columns = ['School Name'] + [available_metrics[metric_category][m]['label'] for m in selected_metrics]
            st.dataframe(display_df, use_container_width=True)

            # Show visualizations
            st.subheader("📈 Visual Comparison")
            numeric_df = st.session_state.df[st.session_state.df['school_name'].isin(st.session_state.selected_schools)].copy()
            for metric in selected_metrics:
                if metric not in ['city', 'state', 'zip']:
                    fig = px.bar(
                        numeric_df,
                        x='school_name',
                        y=metric,
                        title=available_metrics[metric_category][metric]['label'],
                        labels={'school_name': 'School', 
                               metric: available_metrics[metric_category][metric]['label']},
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)

            # Download options
            st.subheader("📥 Download Comparison")
            download_format = st.radio("Choose download format:", ["CSV", "Excel"])
            
            if download_format == "CSV":
                csv = comparison_df[['school_name'] + selected_metrics].to_csv(index=False)
                st.download_button(
                    label="Download as CSV",
                    data=csv,
                    file_name=f"school_comparison_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                )
            else:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer) as writer:
                    comparison_df[['school_name'] + selected_metrics].to_excel(writer, index=False)
                st.download_button(
                    label="Download as Excel",
                    data=buffer.getvalue(),
                    file_name=f"school_comparison_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.ms-excel",
                )

            # Similar schools suggestion
            st.subheader("📚 Similar Schools")
            similar_schools = st.session_state.df[
                (st.session_state.df['state'].isin(st.session_state.df[st.session_state.df['school_name'].isin(st.session_state.selected_schools)]['state'])) &
                (~st.session_state.df['school_name'].isin(st.session_state.selected_schools))
            ].sample(n=min(3, len(st.session_state.df)))
            
            st.markdown("You might also be interested in comparing with these schools:")
            for _, school in similar_schools.iterrows():
                st.markdown(f"- {school['school_name']} ({school['city']}, {school['state']})")

    else:
        st.info("👆 Start by selecting schools to compare from the dropdown above.")

    # Add helpful resources in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📚 Helpful Resources")
    st.sidebar.markdown("""
    - [College Scorecard](https://collegescorecard.ed.gov/)
    - [Federal Student Aid](https://studentaid.gov)
    - [FAFSA Application](https://studentaid.gov/h/apply-for-aid/fafsa)
    """)

# Task 4: Contact Financial Aid Office
elif task == "Contact Financial Aid Office":
    st.header("📞 Contact the Financial Aid Office of Your Selected School")

    # Search bar for school names
    search_query = st.text_input("🔍 Search for a school by name")

    # Filter the schools based on search query
    filtered_df = st.session_state.df[st.session_state.df['school_name'].str.contains(search_query, case=False, na=False)] if search_query else st.session_state.df

    # Always show dropdown with all schools, but display warning if no matches
    if filtered_df.empty:
        st.warning("No schools found matching your search criteria.")
        school_options = st.session_state.df['school_name'].unique()
    else:
        school_options = filtered_df['school_name'].unique()
        
    school_name = st.selectbox("Select a school", school_options)

    # Get the selected school's information
    school_data = filtered_df[filtered_df['school_name'] == school_name]
    if school_data.empty:
        st.error("Selected school data not found.")
        st.stop()
        
    selected_school = school_data.iloc[0]
    school_url = selected_school.get('school_url', 'Not Available')

    # Add http:// prefix if the URL doesn't start with http:// or https://
    if school_url and school_url != 'Not Available' and not school_url.startswith(('http://', 'https://')):
        school_url = 'https://' + school_url

    # Display contact information with an icon
    if school_url and school_url != 'Not Available':
        st.info(f"For more information, you can visit the financial aid page of **{school_name}**:")
        st.markdown(f"[🌐 Visit Financial Aid Office]({school_url})", unsafe_allow_html=True)
    else:
        st.info(f"No website information available for **{school_name}**.")

# Task 5: Scholarship Search
elif task == "Scholarship Search":
    st.header("💰 Financial Aid & Scholarship Resources")
    
    st.markdown("""
        ### Understanding Your Financial Aid Options
        
        Financial aid comes in several forms, and it's important to understand all your options:
    """)
    
    # Types of Financial Aid
    with st.expander("📚 Types of Financial Aid"):
        st.markdown("""
            #### 1. Federal Aid
            - **Grants** (e.g., Pell Grant): Money that doesn't need to be repaid
            - **Work-Study**: Part-time jobs for students with financial need
            - **Federal Student Loans**: Borrowed money with generally lower interest rates
            
            #### 2. State Aid
            - State-specific grants and scholarships
            - State loan programs
            
            #### 3. Institutional Aid
            - Merit-based scholarships
            - Need-based grants
            - Athletic scholarships
            
            #### 4. Private Scholarships
            - Merit-based awards
            - Interest-specific scholarships
            - Organization-sponsored awards
        """)
    
    # FAFSA Information
    with st.expander("📝 About FAFSA"):
        st.markdown("""
            ### Free Application for Federal Student Aid (FAFSA)
            
            **Key Things to Know:**
            - FAFSA is the gateway to federal financial aid
            - Application opens October 1st each year
            - Earlier submission recommended for better aid chances
            - Required documents include:
                - Social Security Number
                - Federal tax returns
                - Records of untaxed income
                - Bank statements
                - List of schools you're interested in
            
            [Complete the FAFSA →](https://studentaid.gov/h/apply-for-aid/fafsa)
        """)
    
    # Scholarship Search Tools
    st.subheader("🔍 Find Scholarships")
    st.markdown("""
        ### Popular Scholarship Search Tools:
        - [FastWeb](https://www.fastweb.com)
        - [Scholarships.com](https://www.scholarships.com)
        - [College Board Scholarship Search](https://bigfuture.collegeboard.org/scholarship-search)
        - [Niche](https://www.niche.com/colleges/scholarships/)
    """)
    
    # Timeline and Deadlines
    with st.expander("📅 Important Deadlines & Timeline"):
        st.markdown("""
            ### Key Financial Aid Deadlines
            
            #### FAFSA
            - Opens: October 1st
            - Federal Deadline: June 30th
            - State/College Deadlines: Usually much earlier
            
            #### CSS Profile (Required by some private colleges)
            - Opens: October 1st
            - Deadlines: Vary by institution
            
            #### Tips:
            - Apply early for best consideration
            - Check individual school deadlines
            - Set calendar reminders for deadlines
            - Keep copies of all submitted documents
        """)
    
    # Financial Aid Tips
    with st.expander("💡 Tips for Maximizing Aid"):
        st.markdown("""
            ### Strategies to Maximize Your Aid
            
            1. **Submit FAFSA Early**
               - Some aid is first-come, first-served
               
            2. **Apply to Multiple Sources**
               - Federal aid
               - State programs
               - Institutional aid
               - Private scholarships
               
            3. **Appeal If Needed**
               - Contact financial aid offices if circumstances change
               - Submit appeals with documentation
               
            4. **Consider All Options**
               - Merit-based aid
               - Need-based aid
               - Work-study programs
               - Payment plans
        """)
    
    # Contact Information
    st.info("""
        ### 📞 Need Help?
        - Federal Student Aid Information Center: 1-800-4-FED-AID (1-800-433-3243)
        - Reach out to your school's financial aid office
    """)
    
    # Additional Resources
    st.markdown("""
        ### 📚 Additional Resources
        - [Federal Student Aid Website](https://studentaid.gov)
        - [College Affordability Guide](https://www.collegeaffordabilityguide.org)
        - [Understanding Student Loans](https://www.consumerfinance.gov/paying-for-college/)
    """)

# # ─── Feature Implementations ───────────────────────────────────────────────────
# if task == "Student Reviews & Insights":
#     st.header("📚 Student Reviews & Insights")
#     school = st.selectbox("Select School", df['school_name'].unique())
    
#     if school:
#         school_info = df[df['school_name'] == school].iloc[0]
        
#         with st.spinner("Gathering student insights..."):
#             unigo_df = fetch_unigo_reviews(school_info['unit_id'])
#             collegewise_df = fetch_collegewise_reviews(school)
#             combined_reviews = pd.concat([unigo_df, collegewise_df], ignore_index=True)
        
#         if not combined_reviews.empty:
#             st.subheader("Recent Student Reviews")
#             for _, review in combined_reviews.head(5).iterrows():
#                 with st.expander(f"⭐ {review['rating']} - {review['author']}"):
#                     st.write(review['text'])
            
#             avg_rating = combined_reviews['rating'].mean()
#             st.metric("Average Rating", f"{avg_rating:.1f}/5")
#         else:
#             st.info("No reviews available for this school")

# elif task == "Transfer Admissions Dashboard":
#     st.header("🔄 Transfer Admissions Insights")
#     school = st.selectbox("Select School", df['school_name'].unique())
    
#     if school:
#         school_data = df[df['school_name'] == school].iloc[0]
        
#         col1, col2, col3 = st.columns(3)
#         col1.metric("Transfer Acceptance Rate", 
#                    f"{school_data.get('transfer_admit_rate', 0)*100:.1f}%" if pd.notna(school_data.get('transfer_admit_rate')) else "N/A")
        
#         col2.metric("Avg Credits Accepted", 
#                    f"{school_data.get('transfer_credit_acceptance', 0):.0f}" if pd.notna(school_data.get('transfer_credit_acceptance')) else "N/A")
        
#         col3.metric("Articulation Agreements", 
#                    "Available" if school_data.get('articulation_partners') else "None Reported")

# elif task == "Campus Visit Planner":
#     st.header("🗺️ Campus Visit Planner")
#     school = st.selectbox("Select School", df['school_name'].unique())
    
#     if school:
#         school_data = df[df['school_name'] == school].iloc[0]
#         events_df = fetch_campus_events(school_data['school_url'])
        
#         if not events_df.empty:
#             st.subheader("Upcoming Events")
#             st.map(events_df[['latitude', 'longitude']], zoom=12)
            
#             with st.expander("Event Details"):
#                 st.dataframe(events_df[['name', 'date']], hide_index=True)
#         else:
#             st.info("No upcoming events found for this campus")

