from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.resources import load_mcp_resources
from typing import Dict, Any, Optional, cast
from langchain_mcp_adapters.sessions import Connection as MCPConnection

from mcp_servers import fetch_mcp_servers_as_config

class MCPManager:
    """
    High-level wrapper around LangChain's MultiServerMCPClient.
    Dynamically manages multiple MCP servers and exposes tools, resources, and prompts.
    """

    def __init__(self, server_configs: Optional[Dict[str, MCPConnection]] = None):
        if server_configs is None:
            server_configs = cast(Dict[str, MCPConnection], fetch_mcp_servers_as_config())
        self.server_configs = server_configs
        self.client = MultiServerMCPClient(self.server_configs)
        self.sessions = {}  # Store persistent session context managers
        self.active_sessions = {}  # Store active session objects

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
            tools, failures, resources = await self.get_tools_with_failures()
            if failures:
                print(f"MCPManager: Some servers failed ({len(failures)} failures), but {len(tools)} tools loaded successfully")
                # Return tools and resources even if some servers failed
                return tools, resources
            else:
                print(f"MCPManager: Successfully fetched {len(tools)} tools from all servers")
                return tools, resources
        except Exception as e:
            print(f"MCPManager: Error fetching tools: {e}")
            import traceback
            traceback.print_exc()
            # Return empty lists for both tools and resources
            return [], []

    async def get_tools_with_failures(self):
        """Fetch all available tools from configured MCP servers, handling individual failures gracefully.

        Returns:
            tuple: (tools_list, failed_servers_dict, resources_list)
                - tools_list: List of successfully loaded tools
                - failed_servers_dict: Dict mapping server names to their error messages
                - resources_list: List of successfully loaded resources
        """
        all_tools = []
        all_resources = []
        failed_servers = {}

        print("MCPManager: Attempting to fetch tools with individual failure handling...")

        # Process each server individually to handle failures gracefully
        for server_name, connection in self.client.connections.items():
            try:
                print(f"MCPManager: Fetching tools from server '{server_name}'...")
                # Open persistent session using context manager but store it properly
                session_cm = self.client.session(server_name)
                session = await session_cm.__aenter__()
                self.sessions[server_name] = session_cm  # Store the context manager
                self.active_sessions[server_name] = session  # Store the session object
                tools = await load_mcp_tools(session)
                # Try to get resources, but handle "Method not found" gracefully
                try:
                    resources = await load_mcp_resources(session)
                except Exception as resource_error:
                    if "Method not found" in str(resource_error):
                        print(f"MCPManager: Server '{server_name}' doesn't support resources method, continuing with tools only")
                        resources = []
                    else:
                        # Re-raise if it's a different error
                        raise resource_error
                if tools:
                    all_tools.extend(tools)
                    print(f"MCPManager: Successfully loaded {len(tools)} tools from '{server_name}'")
                else:
                    print(f"MCPManager: No tools returned from '{server_name}'")
                if resources:
                    all_resources.extend(resources)
                    print(f"MCPManager: Successfully loaded {len(resources)} resources from '{server_name}'")
                else:
                    print(f"MCPManager: No resources returned from '{server_name}'")
            except Exception as e:
                error_msg = str(e)
                print(f"MCPManager: Failed to load tools from '{server_name}': {error_msg}")

                # Provide more detailed error information for common issues
                if "401 Unauthorized" in error_msg:
                    error_msg += " - This indicates an authentication issue with the remote MCP server. Please check your API key or authentication credentials."
                elif "TaskGroup" in error_msg and "unhandled errors" in error_msg:
                    # This might contain a 401 error, let's provide a general auth error message
                    error_msg += " - This indicates an issue with the connection to the remote MCP server. This could be due to authentication problems, network issues, or server configuration errors."
                elif "Connection refused" in error_msg:
                    error_msg += " - This indicates that the server is not reachable. Please check the URL and ensure the server is running."
                elif "timeout" in error_msg.lower():
                    error_msg += " - This indicates a timeout error. The server might be slow to respond or unreachable."

                failed_servers[server_name] = error_msg
                import traceback
                traceback.print_exc()

        print(f"MCPManager: Total tools loaded: {len(all_tools)}")
        print(f"MCPManager: Total resources loaded: {len(all_resources)}")
        if failed_servers:
            print(f"MCPManager: Failed servers: {list(failed_servers.keys())}")

        return all_tools, failed_servers, all_resources

    async def get_resources(self):
        """Fetch all available resources from configured MCP servers with individual failure handling."""
        try:
            print("MCPManager: Attempting to fetch resources...")
            # Use the failure-tolerant method to get resources
            tools, failures, resources = await self.get_tools_with_failures()
            if failures:
                print(f"MCPManager: Some servers failed ({len(failures)} failures), but {len(resources)} resources loaded successfully")
                return resources, failures
            else:
                print(f"MCPManager: Successfully fetched {len(resources)} resources from all servers")
                return resources, failures
        except Exception as e:
            print(f"MCPManager: Error fetching resources: {e}")
            import traceback
            traceback.print_exc()
            # Return empty list for resources and empty dict for failures
            return [], {}

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
            # Try to get tools from this specific server using session
            async with self.client.session(server_name) as session:
                tools = await load_mcp_tools(session)
                # Try to get resources, but handle "Method not found" gracefully
                try:
                    resources = await load_mcp_resources(session)
                except Exception as resource_error:
                    if "Method not found" in str(resource_error):
                        print(f"MCPManager: Server '{server_name}' doesn't support resources method, continuing with tools only")
                        resources = []
                    else:
                        # Re-raise if it's a different error
                        raise resource_error
            print(f"MCPManager: Tools fetched from '{server_name}': {tools}")
            print(f"MCPManager: Resources fetched from '{server_name}': {resources}")

            total_items = len(tools) + len(resources)
            if total_items > 0:
                print(f"MCPManager: Successfully connected to '{server_name}' - {len(tools)} tools and {len(resources)} resources available")
                return "success", f"{len(tools)} tools and {len(resources)} resources available"
            else:
                print(f"MCPManager: Connected to '{server_name}' but no tools or resources returned")
                return "no_tools", "Server connected but no tools or resources available"

        except Exception as e:
            print(f"Error:- {e}")
            error_msg = str(e)
            print(f"MCPManager: Connection test failed for '{server_name}': {error_msg}")
            
            # Print full traceback for debugging
            import traceback
            traceback.print_exc()
            
            # Provide more detailed error information for common issues
            if "401 Unauthorized" in error_msg:
                error_msg += " - This indicates an authentication issue with the remote MCP server. Please check your API key or authentication credentials."
            elif "Method not found" in error_msg:
                error_msg += " - This indicates that the server doesn't support the requested method. This is common with some MCP implementations that don't support all optional methods."
            elif "TaskGroup" in error_msg and "unhandled errors" in error_msg:
                # This might contain a 401 error, let's provide a general auth error message
                error_msg += " - This indicates an issue with the connection to the remote MCP server. This could be due to authentication problems, network issues, or server configuration errors."
            elif "Connection refused" in error_msg:
                error_msg += " - This indicates that the server is not reachable. Please check the URL and ensure the server is running."
            elif "timeout" in error_msg.lower():
                error_msg += " - This indicates a timeout error. The server might be slow to respond or unreachable."
            
            return "error", error_msg

    async def close_sessions(self):
        """Close all persistent sessions."""
        for server_name, session in self.sessions.items():
            try:
                await session.__aexit__(None, None, None)
                print(f"MCPManager: Closed session for '{server_name}'")
            except Exception as e:
                print(f"MCPManager: Error closing session for '{server_name}': {e}")
        self.sessions.clear()

    async def refresh(self, new_configs: Dict[str, MCPConnection]):
        """Hot-reload configuration and reinitialize the MultiServerMCPClient."""
        try:
            # Close existing sessions before refreshing
            await self.close_sessions()
            self.server_configs = new_configs
            self.client = MultiServerMCPClient(new_configs)
            print("MCPManager: Successfully refreshed configuration")
        except Exception as e:
            print(f"MCPManager: Error refreshing configuration: {e}")
            import traceback
            traceback.print_exc()