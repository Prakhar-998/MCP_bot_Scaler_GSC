from mcp.server.fastmcp import FastMCP
from google.oauth2 import service_account
from googleapiclient.discovery import build
import datetime

# Initialize
mcp = FastMCP("GSC-Manager-Bot")

# ==========================================
# CONFIGURATION
# ==========================================
# Make sure this is 'sc-domain:scaler.com'
SITE_URL = 'sc-domain:scaler.com'  
KEY_FILE_LOCATION = 'service_account.json' 
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']

def get_gsc_service():
    """Authenticates and returns the GSC service object."""
    try:
        creds = service_account.Credentials.from_service_account_file(
            KEY_FILE_LOCATION, scopes=SCOPES)
        return build('webmasters', 'v3', credentials=creds)
    except Exception as e:
        raise RuntimeError(f"Authentication failed: {e}")

@mcp.tool()
def get_search_analytics(
    days_ago: int = 7, 
    dimension: str = 'query', 
    limit: int = 10,
    filter_country: str = None,
    filter_page_contains: str = None
) -> str:
    """
    Advanced GSC Analytics Tool.
    
    Args:
        days_ago: Days to look back (default 7).
        dimension: Group by 'query', 'page', 'country', 'device', or 'date'.
        limit: Number of rows to return (default 10).
        filter_country: Filter by 3-letter country code (e.g., 'IND', 'USA').
        filter_page_contains: Filter URLs that contain this string (e.g., '/blog/').
    """
    service = get_gsc_service()
    
    # Date Logic
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days_ago)
    
    # 1. Base Request
    request = {
        'startDate': start_date.isoformat(),
        'endDate': end_date.isoformat(),
        'dimensions': [dimension], 
        'rowLimit': limit,
        'dimensionFilterGroups': []
    }

    # 2. Dynamic Filtering
    filters = []
    
    # Country Filter
    if filter_country:
        filters.append({
            'dimension': 'country',
            'operator': 'equals',
            'expression': filter_country.upper()
        })
        
    # Page URL Filter (New!)
    if filter_page_contains:
        filters.append({
            'dimension': 'page',
            'operator': 'contains',
            'expression': filter_page_contains
        })

    if filters:
        request['dimensionFilterGroups'].append({'filters': filters})

    try:
        print(f"DEBUG: Querying {dimension} | Limit: {limit} | Filters: {filters}")
        response = service.searchanalytics().query(
            siteUrl=SITE_URL, 
            body=request
        ).execute()
        
        rows = response.get('rows', [])
        
        if not rows:
            return f"No data found for {dimension} in the last {days_ago} days."
            
        # 3. Formatted Output (Markdown Table)
        result_text = f"### Top {limit} {dimension}s (Last {days_ago} days)\n"
        if filter_country: result_text += f"- **Country:** {filter_country}\n"
        if filter_page_contains: result_text += f"- **URL Pattern:** '{filter_page_contains}'\n"
        
        result_text += "\n| Key | Clicks | Impressions | CTR | Position |\n"
        result_text += "| :--- | :--- | :--- | :--- | :--- |\n"
        
        for row in rows:
            key = row['keys'][0]
            # If grouping by page, shorten the URL for readability
            if dimension == 'page':
                key = key.replace("https://www.scaler.com", "") or "/"
                
            clicks = row['clicks']
            impressions = row['impressions']
            ctr = row['ctr']
            pos = row['position']
            result_text += f"| {key} | {clicks} | {impressions} | {ctr:.1%} | {pos:.1f} |\n"
            
        return result_text

    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    mcp.run()