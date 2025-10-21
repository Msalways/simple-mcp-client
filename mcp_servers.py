import json
from database import DatabaseManager
from typing import Dict, Any

def fetch_mcp_servers_as_config() -> Dict[str, Dict[str, Any]]:
    """Fetch MCP servers from database and format them as server_config."""
    db_manager = DatabaseManager()
    servers = db_manager.get_mcp_servers()

    server_config = {}
    for server in servers:
        # Skip invalid configurations
        if server['transport'] == 'stdio' and not server['command']:
            print(f"Warning: Skipping server '{server['name']}' due to missing command for stdio transport")
            continue

        if server['transport'] in ['http', 'sse'] and not server['url']:
            print(f"Warning: Skipping server '{server['name']}' due to missing URL for {server['transport']} transport")
            continue

        # Map transport names to langchain-mcp-adapters expected names
        transport = server['transport']
        if transport == 'http':
            transport = 'streamable_http'

        server_config[server['name']] = {
            "transport": transport,
        }

        # Add transport-specific fields
        if server['transport'] == 'stdio':
            if server['command']:
                server_config[server['name']]["command"] = server['command']
            if server['args']:
                # Args from database are already parsed as list or dict
                server_config[server['name']]["args"] = server['args']
                print(f"Added stdio server '{server['name']}' with args: {server['args']}")
        elif server['transport'] in ['streamable_http', 'sse']:
            if server['url']:
                server_config[server['name']]["url"] = server['url']
            if server['args']:
                # Args from database are already parsed as dict or list
                server_config[server['name']]["args"] = server['args']
                print(f"Added {server['transport']} server '{server['name']}' with args: {server_config[server['name']]['args']}")

    print(f"Final server config: {server_config}")
    return server_config

# Existing server_config for backward compatibility
server_config = {
    "math": {
        "transport": "stdio",  # Local subprocess communication
        "command": "python",
        # Absolute path to your math_server.py file
        "args": ["mcp_servers/math.py"],
    },
    # "weather": {
    #     "transport": "streamable_http",  # HTTP-based remote server
    #     # Ensure you start your weather server on port 8000
    #     "url": "http://localhost:8000/mcp",
    # }
}