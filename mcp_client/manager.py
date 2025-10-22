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
        """Fetch all available tools from configured MCP servers with individual failure handling."""
        try:
            print("MCPManager: Attempting to fetch tools...")
            # Use the failure-tolerant method instead of the raw client method
            tools, failures = await self.get_tools_with_failures()
            if failures:
                print(f"MCPManager: Some servers failed ({len(failures)} failures), but {len(tools)} tools loaded successfully")
                # Don't return empty list if we have successful tools
                if tools:
                    return tools
                else:
                    print("MCPManager: No tools loaded successfully from any server")
                    return []
            else:
                print(f"MCPManager: Successfully fetched {len(tools)} tools from all servers")
                return tools
        except Exception as e:
            print(f"MCPManager: Error fetching tools: {e}")
            import traceback
            traceback.print_exc()
            # Return an empty list but also provide error information
            return []

    async def get_tools_with_failures(self):
        """Fetch all available tools from configured MCP servers, handling individual failures gracefully.

        Returns:
            tuple: (tools_list, failed_servers_dict)
                - tools_list: List of successfully loaded tools
                - failed_servers_dict: Dict mapping server names to their error messages
        """
        all_tools = []
        failed_servers = {}

        print("MCPManager: Attempting to fetch tools with individual failure handling...")

        # Process each server individually to handle failures gracefully
        for server_name, connection in self.client.connections.items():
            try:
                print(f"MCPManager: Fetching tools from server '{server_name}'...")
                tools = await self.client.get_tools(server_name=server_name)
                if tools:
                    all_tools.extend(tools)
                    print(f"MCPManager: Successfully loaded {len(tools)} tools from '{server_name}'")
                else:
                    print(f"MCPManager: No tools returned from '{server_name}'")
            except Exception as e:
                error_msg = str(e)
                print(f"MCPManager: Failed to load tools from '{server_name}': {error_msg}")
                
                # Provide more detailed error information for HTTP 401 errors
                # Check if it's an exception group and extract the underlying error
                if "401 Unauthorized" in error_msg:
                    error_msg += " - This indicates an authentication issue with the remote MCP server. Please check your API key or authentication credentials."
                elif "TaskGroup" in error_msg and "unhandled errors" in error_msg:
                    # This might contain a 401 error, let's provide a general auth error message
                    error_msg += " - This may indicate an authentication issue with the remote MCP server. Please check your API key or authentication credentials."
                
                failed_servers[server_name] = error_msg
                import traceback
                traceback.print_exc()

        print(f"MCPManager: Total tools loaded: {len(all_tools)}")
        if failed_servers:
            print(f"MCPManager: Failed servers: {list(failed_servers.keys())}")

        return all_tools, failed_servers

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
        """Test connection to a specific MCP server by attempting to get its tools.

        Returns:
            tuple: (status, details)
                - status: "success", "error", or "no_tools"
                - details: Either tool count, error message, or additional info
        """
        try:
            print(f"MCPManager: Testing connection to server '{server_name}'...")

            if server_name not in self.client.connections:
                return "error", f"Server '{server_name}' not found in configuration"

            print(f"{self.client.connections.get(server_name)} Config")
            # Try to get tools from this specific server
            tools = await self.client.get_tools(server_name=server_name)
            print(f"MCPManager: Tools fetched from '{server_name}': {tools}")

            if tools and len(tools) > 0:
                print(f"MCPManager: Successfully connected to '{server_name}' - {len(tools)} tools available")
                return "success", f"{len(tools)} tools available"
            else:
                print(f"MCPManager: Connected to '{server_name}' but no tools returned")
                return "no_tools", "Server connected but no tools available"

        except Exception as e:
            print(f"Error:- {e}")
            error_msg = str(e)
            print(f"MCPManager: Connection test failed for '{server_name}': {error_msg}")
            
            # Provide more detailed error information for HTTP 401 errors
            # Check if it's an exception group and extract the underlying error
            if "401 Unauthorized" in error_msg:
                error_msg += " - This indicates an authentication issue with the remote MCP server. Please check your API key or authentication credentials."
            elif "TaskGroup" in error_msg and "unhandled errors" in error_msg:
                # This might contain a 401 error, let's provide a general auth error message
                error_msg += " - This may indicate an authentication issue with the remote MCP server. Please check your API key or authentication credentials."
            
            return "error", error_msg

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