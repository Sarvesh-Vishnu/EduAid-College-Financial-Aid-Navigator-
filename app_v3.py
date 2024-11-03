import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
from datetime import datetime
import io

# Add at the start of your script
if 'df' not in st.session_state:
    try:
        st.session_state.df = pd.read_csv('college_scorecard_data.csv')
    except FileNotFoundError:
        st.error("Error: Could not find the college data file. Please check the file path.")
        st.stop()

# Add data validation
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

# Add the "Built with love" message immediately after task selection
st.sidebar.markdown("---")
st.sidebar.markdown("""
    #### Built with 💙 by
    ### Empowering Education Inc.
    [Visit our website](https://www.empoweringeducationfund.org/)
""")

# Rest of your sidebar content (if any) goes here

# Task 1: Find Net Price Calculator
if task == "Find Net Price Calculator":
    st.header("🔗 Find a Net Price Calculator for Your Selected School")

    # Search bar for school names
    search_query = st.text_input("🔍 Search for a school by name")

    # Filter the schools based on search query
    filtered_df = st.session_state.df[st.session_state.df['school_name'].str.contains(search_query, case=False, na=False)] if search_query else st.session_state.df

    # Dropdown for school selection
    school_name = st.selectbox("Select a school", filtered_df['school_name'].unique())

    # Get the NPC URL for the selected school
    selected_school = filtered_df[filtered_df['school_name'] == school_name].iloc[0]
    npc_url = selected_school.get('price_calculator_url', '')

    # Add http:// prefix if the URL doesn't start with http:// or https://
    if npc_url and not npc_url.startswith(('http://', 'https://')):
        npc_url = 'https://' + npc_url

    # Display the NPC link with styling
    if npc_url:
        st.success(f"✅ Visit the Net Price Calculator for **{school_name}**:")
        st.markdown(f"[📄 Net Price Calculator]({npc_url})", unsafe_allow_html=True)
    else:
        st.error(f"No Net Price Calculator link is available for **{school_name}**.")

# Task 2: Research School Financial Aid
elif task == "Research School Financial Aid":
    st.header("💡 Research Financial Aid Information for Selected School")

    try:
        # Search bar for school names
        search_query = st.text_input("🔍 Search for a school by name")

        # Filter the schools based on search query
        filtered_df = st.session_state.df[st.session_state.df['school_name'].str.contains(search_query, case=False, na=False)] if search_query else st.session_state.df

        # Always show dropdown with all schools, but display warning if no matches
        if filtered_df.empty:
            st.warning("No schools found matching your search criteria.")
            school_options = st.session_state.df['school_name'].unique()  # Show all schools instead
        else:
            school_options = filtered_df['school_name'].unique()
            
        school_name = st.selectbox("Select a school", school_options)

        # Get the selected school's information with additional error handling
        school_data = filtered_df[filtered_df['school_name'] == school_name]
        if school_data.empty:
            st.error("Selected school data not found.")
            st.stop()
            
        selected_school = school_data.iloc[0]

        # Display school financial aid information in columns for better layout
        col1, col2 = st.columns(2)
        
        # Helper function to format metrics with error handling
        def display_metric(col, label, value_key, is_percentage=False, is_currency=False):
            try:
                value = selected_school[value_key]
                if pd.isna(value):
                    col.error(f"{label}: Data not available")
                else:
                    if is_percentage:
                        formatted_value = f"{value*100:.2f}%"
                    elif is_currency:
                        formatted_value = f"${value:,.0f}"
                    else:
                        formatted_value = f"{value:.0f}"
                    col.metric(label=label, value=formatted_value)
            except (KeyError, TypeError):
                col.error(f"{label}: Data not available")

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
        },
        "Post-Graduation": {
            'median_earnings_10yrs': {'label': 'Median Earnings after 10 years ($)', 'tooltip': 'Median earnings of graduates 10 years after enrollment'},
        }
    }

    # School selection
    search_query = st.text_input("🔍 Search for schools by name")
    filtered_df = st.session_state.df[st.session_state.df['school_name'].str.contains(search_query, case=False, na=False)] if search_query else st.session_state.df
    
    selected_schools = st.multiselect(
        "Select schools to compare (max 5)",
        options=filtered_df['school_name'].unique(),
        max_selections=5
    )

    if selected_schools:
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
            comparison_df = filtered_df[filtered_df['school_name'].isin(selected_schools)].copy()

            # Format the data
            def format_value(value, metric):
                if pd.isna(value):
                    return "N/A"
                if metric in ['in_state_tuition', 'out_of_state_tuition', 'attendance_cost', 
                            'net_price_public', 'net_price_private', 'median_debt', 
                            'median_family_income', 'median_earnings_10yrs']:
                    return f"${value:,.0f}"
                elif metric in ['completion_rate', 'admission_rate', 'first_generation']:
                    return f"{value*100:.1f}%"
                elif metric in ['student_size', 'sat_average']:
                    return f"{int(value):,}"
                elif metric == 'age_entry':
                    return f"{value:.1f} years"
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
            numeric_df = filtered_df[filtered_df['school_name'].isin(selected_schools)].copy()
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
            similar_schools = filtered_df[
                (filtered_df['state'].isin(filtered_df[filtered_df['school_name'].isin(selected_schools)]['state'])) &
                (~filtered_df['school_name'].isin(selected_schools))
            ].sample(n=min(3, len(filtered_df)))
            
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
        st.error(f"No website information available for **{school_name}**.")

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