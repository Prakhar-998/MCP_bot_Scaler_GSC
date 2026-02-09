from mcp.server.fastmcp import FastMCP
from google.oauth2 import service_account
from googleapiclient.discovery import build
import datetime

# Initialize the MCP Server
mcp = FastMCP("GSC-Manager-Bot")

# CONFIGURATION
# 1. The ID of the GSC property (usually the full URL)
SITE_URL = 'https://www.scaler.com/'  
# 2. Your JSON key file path
KEY_FILE_LOCATION = 'service_account.json' 
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']

def get_gsc_service():
    """Authenticates and returns the GSC service object."""
    try:
        creds = service_account.Credentials.from_service_account_file(
            KEY_FILE_LOCATION, scopes=SCOPES)
        return build('webmasters', 'v3', credentials=creds)
    except Exception as e:
        raise RuntimeError(f"Authentication failed. Check your JSON key file: {e}")

@mcp.tool()
def get_search_analytics(days_ago: int = 7, dimension: str = 'query', country_code: str = None) -> str:
    """
    Queries Google Search Console analytics for Scaler.com.
    
    Args:
        days_ago: How many days of data to look back (default 7).
        dimension: What to group by. Options: 'query', 'page', 'country', 'device'.
        country_code: Optional 3-letter country code (e.g., 'IND', 'USA', 'GBR') to filter results.
    """
    service = get_gsc_service()
    
    # Calculate dates: End date is today (API handles the lag automatically)
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days_ago)
    
    # Base Request
    request = {
        'startDate': start_date.isoformat(),
        'endDate': end_date.isoformat(),
        'dimensions': [dimension], 
        'rowLimit': 10,
        'dimensionFilterGroups': [] # Prepared list for filters
    }
    
    # Add Country Filter if requested
    if country_code:
        request['dimensionFilterGroups'].append({
            'filters': [{
                'dimension': 'country',
                'operator': 'equals',
                'expression': country_code.upper()
            }]
        })
    
    try:
        print(f"DEBUG: Fetching data for {dimension} from {start_date} to {end_date}...")
        response = service.searchanalytics().query(
            siteUrl=SITE_URL, 
            body=request
        ).execute()
        
        rows = response.get('rows', [])
        
        if not rows:
            return f"No data found for the last {days_ago} days."
            
        # NEW: Markdown Table Formatting
        result_text = f"### GSC Data for {SITE_URL} (Last {days_ago} days)\n"
        if country_code:
            result_text += f"**Filter:** Country = {country_code.upper()}\n"
            
        result_text += "\n| Dimension | Clicks | Impressions | CTR | Position |\n"
        result_text += "| :--- | :--- | :--- | :--- | :--- |\n"
        
        for row in rows:
            key = row['keys'][0] # The query, page, or country name
            clicks = row['clicks']
            impressions = row['impressions']
            ctr = row['ctr']
            position = row['position']
            
            # Add row to table
            result_text += f"| {key} | {clicks} | {impressions} | {ctr:.1%} | {position:.1f} |\n"
            
        return result_text

    except Exception as e:
        # This is where we will see the permission error if manager hasn't added the user yet
        return f"Error querying GSC: {str(e)}"

if __name__ == "__main__":
    mcp.run()