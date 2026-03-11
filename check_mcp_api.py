import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

async def check():
    mcp_config = {
        "playwright": {
            "command": "npx",
            "args": ["@playwright/mcp", "--headless"],
            "transport": "stdio",
        }
    }
    
    client = MultiServerMCPClient(mcp_config)
    tools = await client.get_tools()
    
    if tools:
        print(f"Got {len(tools)} tools")
        print(f"First tool name: {tools[0].name}")
        print(f"Tool type: {type(tools[0])}")
        print(f"Tool methods: {[m for m in dir(tools[0]) if not m.startswith('_')]}")
        
        # Check if tools can be invoked directly
        if hasattr(tools[0], 'invoke') or hasattr(tools[0], 'ainvoke'):
            print("\n✓ Tools have invoke/ainvoke methods - they are LangChain tools")
        else:
            print("\n✗ Tools don't have invoke methods")
    else:
        print("No tools returned")

asyncio.run(check())
