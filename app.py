import streamlit as st
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
import datetime
import json
import pandas as pd

def check_password():
    """Returns `True` if the user had the correct password."""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    st.text_input(
        "Enter Password", 
        type="password", 
        on_change=password_entered, 
        key="password_input"
    )
    return False

def password_entered():
    if st.session_state["password_input"] == st.secrets["APP_PASSWORD"]:
        st.session_state.password_correct = True
        del st.session_state["password_input"]
    else:
        st.session_state.password_correct = False
        st.error("😕 Password incorrect")

if not check_password():
    st.stop()

# 2. CONFIG
st.set_page_config(page_title="Scaler SEO Intelligence", layout="wide")
st.markdown("""<style>.stChatInput {position: fixed; bottom: 30px; width: 70%; left: 15%;} .block-container {padding-top: 2rem;} h1 {color: #2E86C1;}</style>""", unsafe_allow_html=True)

st.title("Scaler SEO Intelligence")
st.caption("Powered by Google Search Console")

#3. AUTHENTICATION
try:
    if "GENAI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GENAI_API_KEY"])
        GSC_INFO = st.secrets["GSC_SERVICE_ACCOUNT"]
    else:
        st.error("Secrets not found.")
        st.stop()
except Exception as e:
    st.info("Waiting for secrets configuration...")
    st.stop()

@st.cache_data(ttl=3600)
def fetch_gsc_data(days_ago=None, start_date=None, end_date=None, dimension="query", limit=10, filter_country=None, filter_page=None):
    """
    Fetches GSC data and returns it as a lightweight CSV string to save tokens.
    """
    try:
        creds = service_account.Credentials.from_service_account_info(
            json.loads(GSC_INFO), 
            scopes=['https://www.googleapis.com/auth/webmasters.readonly']
        )
        service = build('webmasters', 'v3', credentials=creds)
        
        # 2. Date
        if start_date and end_date:
            final_start = start_date
            final_end = end_date
        else:
            days_count = int(days_ago) if days_ago else 7
            date_end = datetime.date.today()
            date_start = date_end - datetime.timedelta(days=days_count)
            final_start = date_start.isoformat()
            final_end = date_end.isoformat()

        # 3. Build Request
        request = {
            'startDate': final_start,
            'endDate': final_end,
            'dimensions': [dimension],
            'rowLimit': limit,
            'dimensionFilterGroups': []
        }
        
        # Filters
        filters = []
        if filter_country:
            filters.append({'dimension': 'country', 'operator': 'equals', 'expression': filter_country.upper()})
        if filter_page:
            filters.append({'dimension': 'page', 'operator': 'contains', 'expression': filter_page})
        if filters:
            request['dimensionFilterGroups'].append({'filters': filters})

        # 4. Execute
        response = service.searchanalytics().query(
            siteUrl='sc-domain:scaler.com', 
            body=request
        ).execute()
        
        rows = response.get('rows', [])
        
        if not rows:
            return "No data found for this period."

        # 5. CSV MINIFIER (The Token Saver)
        output = []
        # Create Header
        header = f"{dimension},clicks,impressions,ctr,position"
        output.append(header)
        
        # Parse Rows
        for row in rows:
            key_val = row['keys'][0]
            # Clean commas to prevent CSV breakage
            clean_key = str(key_val).replace(',', '') 
            
            line = f"{clean_key},{row['clicks']},{row['impressions']},{row['ctr']},{row['position']}"
            output.append(line)
            
        # Return single string
        return "\n".join(output)

    except Exception as e:
        return f"Error fetching GSC data: {str(e)}"

# --- 5. THE AI MODEL ---
today_date = datetime.date.today().strftime("%Y-%m-%d")

sys_instruct = f"""
You are a technical SEO Analyst for Scaler. 
TODAY'S DATE is {today_date}.

TOOL RULES:
1. If the user asks for a SPECIFIC DATE RANGE (e.g., "January 2025"), calculate 'start_date' and 'end_date' (YYYY-MM-DD).
2. If the user asks for a RELATIVE RANGE (e.g., "Last 7 days"), use 'days_ago'.
3. The tool returns CSV data. Analyze the numbers in the CSV to answer.
"""

model = genai.GenerativeModel(
    'gemini-3-flash', 
    tools=[fetch_gsc_data], 
    system_instruction=sys_instruct
)

# 6. THE UI
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "Hello! I'm connected to Scaler's GSC. Ask me about traffic, queries, or pages."})

with st.sidebar:
    st.header("⚡ Quick Actions")
    if st.button("🇮🇳 India Performance (7 Days)"):
        st.session_state.prompt_trigger = "How is our organic traffic in India over the last 7 days?"
    if st.button("🔍 Top 10 Queries (Global)"):
        st.session_state.prompt_trigger = "List the top 10 queries by clicks for the last 7 days globally."
    st.divider()
    st.caption(f"📅 System Date: {today_date}")
    st.success("System: Online ✅")
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# Chat Logic
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Ask a question...")

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
                # Automatic Function Calling executes the tool and gets the CSV
                chat = model.start_chat(enable_automatic_function_calling=True)
                response = chat.send_message(user_input)
                
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")