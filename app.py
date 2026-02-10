import streamlit as st
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
import datetime
import json
import pandas as pd
import datetime

# ... other imports ...

# ---------------------------------------------------------
# 1. GATEKEEPER (MUST BE FIRST)
# ---------------------------------------------------------
def check_password():
    """Returns `True` if the user had the correct password."""
    
    # Initialize state
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    # If already correct, return True immediately
    if st.session_state.password_correct:
        return True

    # Show input for password
    st.text_input(
        "Enter Password", 
        type="password", 
        on_change=password_entered, 
        key="password_input"
    )
    return False

def password_entered():
    """Checks whether a password entered by the user is correct."""
    if st.session_state["password_input"] == st.secrets["APP_PASSWORD"]:
        st.session_state.password_correct = True
        del st.session_state["password_input"]  # Clean up
    else:
        st.session_state.password_correct = False
        st.error("😕 Password incorrect")

# EXECUTE THE CHECK
if not check_password():
    st.stop()  # <--- THIS IS CRITICAL. It stops the rest of the file from running!


# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(
    page_title="Scaler SEO Intelligence",
    page_icon="",
    layout="wide"
)

# Custom CSS to make it look polished
st.markdown("""
<style>
    .stChatInput {position: fixed; bottom: 30px; width: 70%; left: 15%;}
    .block-container {padding-top: 2rem;}
    h1 {color: #2E86C1;}
</style>
""", unsafe_allow_html=True)

st.title(" Scaler SEO Intelligence")
st.caption("Powered by Gemini Pro & Google Search Console")

# --- 2. AUTHENTICATION (Secrets) ---
# Setup: Create .streamlit/secrets.toml with your keys
try:
    if "GENAI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GENAI_API_KEY"])
        GSC_INFO = st.secrets["GSC_SERVICE_ACCOUNT"]
    else:
        st.error(" Secrets not found. Please configure .streamlit/secrets.toml")
        st.stop()
except Exception as e:
    st.info("Waiting for secrets configuration...")
    st.stop()

# --- 3. THE BACKEND LOGIC (Cached for Speed) ---
@st.cache_data(ttl=3600)
def fetch_gsc_data(days_ago=None, start_date=None, end_date=None, dimension="query", limit=10, filter_country=None, filter_page=None):
    """
    Fetches GSC data. 
    - Use 'days_ago' for relative dates (e.g., "last 7 days").
    - Use 'start_date' + 'end_date' for specific ranges (YYYY-MM-DD).
    """
    try:
        # 1. SETUP CREDENTIALS
        creds = service_account.Credentials.from_service_account_info(
            json.loads(GSC_INFO), 
            scopes=['https://www.googleapis.com/auth/webmasters.readonly']
        )
        service = build('webmasters', 'v3', credentials=creds)
        
        # 2. DATE LOGIC (The Fix for "January 2025")
        if start_date and end_date:
            # If AI provides specific dates, use them directly
            final_start = start_date
            final_end = end_date
        else:
            # Default to relative "days ago" if no specific dates provided
            # If days_ago is None, default to 7 days to prevent errors
            days_count = int(days_ago) if days_ago else 7
            
            date_end = datetime.date.today()
            date_start = date_end - datetime.timedelta(days=days_count)
            final_start = date_start.isoformat()
            final_end = date_end.isoformat()

        # 3. BUILD REQUEST
        request = {
            'startDate': final_start,
            'endDate': final_end,
            'dimensions': [dimension],
            'rowLimit': limit,
            'dimensionFilterGroups': []
        }
        
        # Add Filters
        filters = []
        if filter_country:
            filters.append({'dimension': 'country', 'operator': 'equals', 'expression': filter_country.upper()})
        if filter_page:
            filters.append({'dimension': 'page', 'operator': 'contains', 'expression': filter_page})
            
        if filters:
            request['dimensionFilterGroups'].append({'filters': filters})

        # 4. EXECUTE QUERY
        response = service.searchanalytics().query(
            siteUrl='sc-domain:scaler.com', 
            body=request
        ).execute()
        
        rows = response.get('rows', [])
        
        if not rows:
            return "No data found for this period."

        # 5. MINIFY OUTPUT (Save Tokens!)
        # Converts heavy JSON into light CSV format
        output = []
        header = f"{dimension},clicks,impressions,ctr,position"
        output.append(header)
        
        for row in rows:
            # 'keys' is always a list, we take the first item
            key_val = row['keys'][0]
            # Remove commas from keywords to keep CSV clean
            clean_key = str(key_val).replace(',', '') 
            
            line = f"{clean_key},{row['clicks']},{row['impressions']},{row['ctr']},{row['position']}"
            output.append(line)
            
        return "\n".join(output)

    except Exception as e:
        return f"Error fetching GSC data: {str(e)}"
# ==========================================
# CRITICAL FIX: Pass the actual function 'fetch_gsc_data', NOT a dictionary.
# This allows 'enable_automatic_function_calling' to actually execute the code.
today_date = datetime.date.today().strftime("%Y-%m-%d")

sys_instruct = f"""
You are a technical SEO Analyst for Scaler. 
TODAY'S DATE is {today_date}.

TOOL RULES:
1. If the user asks for a SPECIFIC DATE RANGE (e.g., "January 2025" or "Dec 1st to Dec 10th"), calculate the 'start_date' and 'end_date' (YYYY-MM-DD) and pass them to the tool. Do NOT use 'days_ago'.
2. If the user asks for a RELATIVE RANGE (e.g., "Last 7 days"), use 'days_ago'.
3. Always analyze the returned CSV data to answer the user's question.
"""

model = genai.GenerativeModel(
    'gemini-2.5-flash', 
    tools=[fetch_gsc_data], 
    system_instruction=sys_instruct
)
# ==========================================
# ==========================================
# 5. THE UI (Chat Interface)
# ==========================================

# Initialize chat history if empty
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "Hello! I'm connected to Scaler's GSC. Ask me about traffic, queries, or pages."})

# ---------------------------------------------------------
# SIDEBAR (Quick Actions)
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚡ Quick Actions")
    
    # Button 1: Traffic Overview
    if st.button("🇮🇳 India Performance (7 Days)"):
        st.session_state.prompt_trigger = "How is our organic traffic in India over the last 7 days?"
    
    # Button 2: Top Queries
    if st.button("🔍 Top 10 Queries (Global)"):
        st.session_state.prompt_trigger = "List the top 10 queries by clicks for the last 7 days globally."
        
    st.divider()
    
    # System Status Indicator
    st.caption(f"📅 System Date: {today_date}")
    st.success("System: Online ✅")
    
    # Clear History Button (Useful for debugging)
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# ---------------------------------------------------------
# MAIN CHAT LOGIC
# ---------------------------------------------------------

# 1. Display existing chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 2. Handle User Input
user_input = st.chat_input("Ask a question...")

# 3. Handle Sidebar Button Triggers
if "prompt_trigger" in st.session_state:
    user_input = st.session_state.prompt_trigger
    del st.session_state.prompt_trigger

# 4. Process the Request
if user_input:
    # Add user message to UI
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Generate Response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing GSC data..."):
            try:
                # Initialize chat with automatic function calling enabled
                chat = model.start_chat(enable_automatic_function_calling=True)
                
                # Send message to Gemini
                response = chat.send_message(user_input)
                
                # Display response
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

    # 2. Gemini Reasoning Loop
    with st.chat_message("assistant"):
        with st.spinner("Analyzing GSC data..."):
            # Start Chat
            chat = model.start_chat(enable_automatic_function_calling=True)
            
            # Send message (Gemini automatically calls the tool logic we defined!)
            # NOTE: For Streamlit, we need to map the tool manually if we don't use the auto-execution context
            # Simpler approach: Manual Tool Call Handling for display clarity
            
            response = chat.send_message(user_input)
            
            # 3. Check if it tried to call a function (Manual Check for better UI)
            # (In this simple version, we let Gemini handle it internally)
            
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})