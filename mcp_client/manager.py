from langchain_mcp_adapters.client import MultiServerMCPClient

from mcp_servers import fetch_mcp_servers_as_config

class MCPManager:
    """
    High-level wrapper around LangChain's MultiServerMCPClient.
    Dynamically manages multiple MCP servers and exposes tools, resources, and prompts.
    """

    def __init__(self, server_configs: dict):
        self.server_configs = fetch_mcp_servers_as_config()
        self.client = MultiServerMCPClient(server_configs)

    async def list_servers(self):
        """List all configured MCP servers."""
        return list(self.client.connections.keys())

    async def get_tools(self):
        """Fetch all available tools from configured MCP servers."""
        try:
            tools = await self.client.get_tools()
            print(f"MCPManager: Successfully fetched {len(tools) if tools else 0} tools")
            return tools
        except Exception as e:
            print(f"MCPManager: Error fetching tools: {e}")
            import traceback
            traceback.print_exc()
            return []

    # async def get_resources(self, server_name):
    #     """Fetch available resources from MCP servers.""" 
    #     return await self.client.get_resources(server_name)

    # async def get_prompts(self, server_name):
    #     """Fetch available prompts from MCP servers."""
    #     return await self.client.get_prompts(server_name)

    async def refresh(self, new_configs: dict):
        """Hot-reload configuration and reinitialize the MultiServerMCPClient."""
        self.server_configs = new_configs
        self.client = MultiServerMCPClient(new_configs)