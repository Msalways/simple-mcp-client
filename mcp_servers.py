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

        # Always ensure args is a list, standardize for all transports
        args_list = server['args'] if server['args'] and isinstance(server['args'], list) else []
        env_dict = server['env'] if server['env'] and isinstance(server['env'], dict) else {}

        # Add transport-specific fields
        if server['transport'] == 'stdio':
            if server['command']:
                server_config[server['name']]["command"] = server['command']
            if args_list:
                server_config[server['name']]["args"] = args_list
                print(f"Added stdio server '{server['name']}' with args: {args_list}")
            if env_dict:
                server_config[server['name']]["env"] = env_dict
        elif server['transport'] in ['http', 'sse']:
            if server['url']:
                server_config[server['name']]["url"] = server['url']
            if args_list:
                # For http/sse, args might be used for additional config if supported
                server_config[server['name']]["args"] = args_list
            if env_dict:
                # For http/sse, env might be used for headers or auth
                server_config[server['name']]["env"] = env_dict

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
}
