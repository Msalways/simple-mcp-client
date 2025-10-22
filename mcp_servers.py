import json
from database import DatabaseManager
from typing import Dict, Any

def fetch_mcp_servers_as_config() -> Dict[str, Dict[str, Any]]:
    """Fetch MCP servers from database and format them as server_config."""
    db_manager = DatabaseManager()
    servers = db_manager.get_mcp_servers()

    server_config = {}
    for server in servers:
        # Get fields with defaults to avoid KeyError
        name = server.get('name', 'unknown')
        transport = server.get('transport', 'unknown')
        command = server.get('command', '')
        url = server.get('url', '')
        args_list = server['args'] if server.get('args') and isinstance(server['args'], list) else []
        env_dict = server['env'] if server.get('env') and isinstance(server['env'], dict) else {}

        # Skip invalid configurations
        if transport == 'stdio' and not command.strip():
            print(f"Warning: Skipping server '{name}' due to missing or invalid command for stdio transport")
            continue

        if transport in ['http', 'sse', 'streamable_http'] and not url.strip():
            print(f"Warning: Skipping server '{name}' due to missing or invalid URL for {transport} transport")
            continue

        # Skip unknown transports
        if transport not in ['stdio', 'streamable_http', 'sse']:
            print(f"Warning: Skipping server '{name}' due to unknown transport '{transport}'")
            continue

        # Map transport names to langchain-mcp-adapters expected names
        mapped_transport = transport
        if transport == 'streamable_http':
            mapped_transport = 'streamable_http'

        server_config[name] = {
            "transport": mapped_transport,
        }

        # Add transport-specific fields
        if transport == 'stdio':
            if command:
                server_config[name]["command"] = command
            if args_list:
                server_config[name]["args"] = args_list
                print(f"Added stdio server '{name}' with args: {args_list}")
            if env_dict:
                server_config[name]["env"] = env_dict
        elif transport in ['http', 'sse', 'streamable_http']:
            if url:
                server_config[name]["url"] = url
            if args_list:
                # For http/sse, args might be used for additional config if supported
                server_config[name]["args"] = args_list
            # Note: env not supported for http/sse transports - would cause TypeError
            # if env_dict:
            #     server_config[name]["env"] = env_dict

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
