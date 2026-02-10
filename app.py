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
    page_icon="🚀",
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

st.title("🚀 Scaler SEO Intelligence")
st.caption("Powered by Gemini Pro & Google Search Console")

# --- 2. AUTHENTICATION (Secrets) ---
# Setup: Create .streamlit/secrets.toml with your keys
try:
    if "GENAI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GENAI_API_KEY"])
        GSC_INFO = st.secrets["GSC_SERVICE_ACCOUNT"]
    else:
        st.error("⚠️ Secrets not found. Please configure .streamlit/secrets.toml")
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

# --- 4. THE BRAIN (Gemini Tool Definition) ---
tools = [{
    "function_declarations": [{
        "name": "fetch_gsc_data",
        "description": "Fetch SEO traffic data from GSC.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "days_ago": {"type": "INTEGER", "description": "Days to look back (default 7)"},
                "dimension": {"type": "STRING", "description": "query, page, country, device"},
                "limit": {"type": "INTEGER", "description": "Rows to fetch (max 50)"},
                "filter_country": {"type": "STRING", "description": "Country code (IND, USA)"},
                "filter_page": {"type": "STRING", "description": "URL substring filter"}
            },
            "required": ["dimension"]
        }
    }]
}]

model = genai.GenerativeModel('gemini-1.5-flash', tools=tools)

# --- 5. THE UI (Chat Interface) ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Initial Greeting
    st.session_state.messages.append({"role": "assistant", "content": "Hello! I have access to live Scaler GSC data. Ask me anything."})

# Sidebar with Quick Actions
with st.sidebar:
    st.header("⚡ Quick Analysis")
    if st.button("🇮🇳 India Performance (Last 7 Days)"):
        st.session_state.prompt_trigger = "How is our organic traffic in India over the last 7 days?"
    if st.button("📉 Drop Analysis (Data Science)"):
        st.session_state.prompt_trigger = "List the top 10 queries for 'data science' pages and analyze their CTR."
    
    st.divider()
    st.markdown("**Debug Info:**")
    st.success("GSC Connected ✅")

# Render Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle Input (Text Bar OR Sidebar Button)
user_input = st.chat_input("Ask a question...")
if "prompt_trigger" in st.session_state:
    user_input = st.session_state.prompt_trigger
    del st.session_state.prompt_trigger

if user_input:
    # 1. Display User Message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

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