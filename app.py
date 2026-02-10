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
@st.cache_data(ttl=3600) # Cache data for 1 hour to save API quota
def fetch_gsc_data(days_ago, dimension, limit, filter_country=None, filter_page=None):
    """The Core Logic from your server.py, adapted for Streamlit"""
    try:
        creds = service_account.Credentials.from_service_account_info(
            json.loads(GSC_INFO), 
            scopes=['https://www.googleapis.com/auth/webmasters.readonly']
        )
        service = build('webmasters', 'v3', credentials=creds)
        
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=days_ago)
        
        request = {
            'startDate': start_date.isoformat(),
            'endDate': end_date.isoformat(),
            'dimensions': [dimension],
            'rowLimit': limit,
            'dimensionFilterGroups': []
        }
        
        filters = []
        if filter_country:
            filters.append({'dimension': 'country', 'operator': 'equals', 'expression': filter_country.upper()})
        if filter_page:
            filters.append({'dimension': 'page', 'operator': 'contains', 'expression': filter_page})
            
        if filters:
            request['dimensionFilterGroups'].append({'filters': filters})

        response = service.searchanalytics().query(
            siteUrl='sc-domain:scaler.com', 
            body=request
        ).execute()
        
        return response.get('rows', [])
    except Exception as e:
        return str(e)

# 4. THE BRAIN (Updated for Gemini 2.5)
# ==========================================
# CRITICAL FIX: Pass the actual function 'fetch_gsc_data', NOT a dictionary.
# This allows 'enable_automatic_function_calling' to actually execute the code.
today_date = datetime.date.today().strftime("%Y-%m-%d")
sys_instruct = f"""
You are a technical SEO Analyst for Scaler. 
TODAY'S DATE is {today_date}.
When a user asks for a specific date (e.g., "January 2025"), YOU must calculate how many 'days_ago' that was relative to {today_date} and use the tool.
Do not ask the user to calculate days. Do it yourself.
"""
model = genai.GenerativeModel('gemini-2.5-flash', tools=[fetch_gsc_data], system_instruction=sys_instruct)

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