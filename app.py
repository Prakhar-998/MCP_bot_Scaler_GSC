import streamlit as st
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
import datetime
import json
import pandas as pd

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
model = genai.GenerativeModel('gemini-2.5-flash', tools=[fetch_gsc_data])

# ==========================================
# 5. THE UI (Chat Interface)
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "Hello! I'm connected to Scaler's GSC. Ask me about traffic, queries, or pages."})

# Sidebar
with st.sidebar:
    st.header("⚡ Quick Actions")
    if st.button("🇮🇳 India Performance (7 Days)"):
        st.session_state.prompt_trigger = "How is our organic traffic in India over the last 7 days?"
    
    st.divider()
    st.success("System: Online ✅")

# Chat Logic
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Ask a question...")

# Handle Sidebar Button Trigger
if "prompt_trigger" in st.session_state:
    user_input = st.session_state.prompt_trigger
    del st.session_state.prompt_trigger

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing GSC data..."):
            try:
                # Initialize chat with automatic execution enabled
                chat = model.start_chat(enable_automatic_function_calling=True)
                
                # Send the message
                # The SDK will now:
                # 1. See the tool call
                # 2. EXECUTE your 'fetch_gsc_data' function automatically
                # 3. Get the data and send it back to Gemini
                # 4. Return the final text answer here
                response = chat.send_message(user_input)
                
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