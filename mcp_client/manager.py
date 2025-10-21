from langchain_mcp_adapters.client import MultiServerMCPClient

from mcp_servers import fetch_mcp_servers_as_config

class MCPManager:
    """
    High-level wrapper around LangChain's MultiServerMCPClient.
    Dynamically manages multiple MCP servers and exposes tools, resources, and prompts.
    """

    def __init__(self, server_configs: dict = None):
        if server_configs is None:
            self.server_configs = fetch_mcp_servers_as_config()
        else:
            self.server_configs = server_configs
        self.client = MultiServerMCPClient(self.server_configs)

    async def list_servers(self):
        """List all configured MCP servers."""
        try:
            return list(self.client.connections.keys())
        except Exception as e:
            print(f"MCPManager: Error listing servers: {e}")
            return []

    async def get_tools(self):
        """Fetch all available tools from configured MCP servers."""
        try:
            print("MCPManager: Attempting to fetch tools...")
            tools = await self.client.get_tools()
            print(f"MCPManager: Successfully fetched {len(tools) if tools else 0} tools")
            return tools
        except Exception as e:
            print(f"MCPManager: Error fetching tools: {e}")
            import traceback
            traceback.print_exc()
            # Return an empty list but also provide error information
            return []

    async def get_connection_status(self):
        """Get the status of all MCP server connections."""
        try:
            status = {}
            # print(await self.client.get_tools())
            for name, connection in self.client.connections.items():
                try:
                    # Check connection status based on connection type
                    # For now, we'll just check if the connection object exists
                    # A more sophisticated check would depend on the specific connection type
                    if connection:
                        status[name] = "Active"
                    else:
                        status[name] = "Inactive"
                except Exception as e:
                    status[name] = f"Error: {str(e)}"
            return status
        except Exception as e:
            print(f"MCPManager: Error getting connection status: {e}")
            return {}

    async def test_server_connection(self, server_name: str):
        """Test connection to a specific MCP server by attempting to get its tools."""
        try:
            print(f"MCPManager: Testing connection to server '{server_name}'...")
            # Try to get tools from this specific server
            session = self.client.session(server_name)
            if session is not None:
                print(f"MCPManager: Successfully connected to '{server_name}'")
                return "Active"
            else:
                print(f"MCPManager: No tools returned from '{server_name}'")
                return "No tools available"
        except Exception as e:
            error_msg = str(e)
            print(f"MCPManager: Connection test failed for '{server_name}': {error_msg}")
            return f"Error: {error_msg}"

    # async def get_resources(self, server_name):
    #     """Fetch available resources from MCP servers.""" 
    #     return await self.client.get_resources(server_name)

    # async def get_prompts(self, server_name):
    #     """Fetch available prompts from MCP servers."""
    #     return await self.client.get_prompts(server_name)

    async def refresh(self, new_configs: dict):
        """Hot-reload configuration and reinitialize the MultiServerMCPClient."""
        try:
            self.server_configs = new_configs
            self.client = MultiServerMCPClient(new_configs)
            print("MCPManager: Successfully refreshed configuration")
        except Exception as e:
            print(f"MCPManager: Error refreshing configuration: {e}")
            import traceback
            traceback.print_exc()