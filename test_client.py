import asyncio
# We import specific classes to fix the 'stdio_client' usage
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_chat_test():
    # 1. Define how to launch your server
    server_params = StdioServerParameters(
        command="python", 
        args=["server.py", "run"], # This keeps the server running!
        env=None
    )

    print("🤖 Connecting to GSC-Manager-Bot...")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # === THE FIX: WE MUST INITIALIZE THE SESSION FIRST ===
            await session.initialize()
            print("✅ Handshake complete!")

            # 2. List available tools
            tools = await session.list_tools()
            print(f"🛠️  Found tool: {tools.tools[0].name}")
            
            # 3. Simulate the Manager asking a question
            print("\n🔍 Querying GSC Data (Simulating chat request)...")
            
            try:
                # We call the tool with the arguments we defined in server.py
                result = await session.call_tool(
                    "get_search_analytics",
                    arguments={"days_ago": 30, "limit": 5,"dimension": "query", "country_code": "IND","filter_page_contains": "data-science"}
                )
                
                # 4. Print the result
                print("\n📊 RESULT FROM SERVER:")
                print("---------------------------------------------------")
                # The result comes back as a list of content blocks
                print(result.content[0].text)
                print("---------------------------------------------------")
                
            except Exception as e:
                print(f"\n❌ Error calling tool: {e}")

if __name__ == "__main__":
    asyncio.run(run_chat_test())