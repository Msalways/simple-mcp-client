from mcp_servers import fetch_mcp_servers_as_config
from mcp_client.manager import MCPManager
import asyncio

async def test_mcp():
    print("Fetching server config...")
    config = fetch_mcp_servers_as_config()
    print(f"Server config: {config}")
    
    print("Creating MCP manager...")
    manager = MCPManager(config)
    
    print("Fetching tools...")
    try:
        tools = await manager.get_tools()
        print(f"Successfully loaded {len(tools)} tools")
        for tool in tools:
            print(f"  - {tool.name}")
    except Exception as e:
        print(f"Error loading tools: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp())