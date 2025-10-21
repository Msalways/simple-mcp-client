#!/usr/bin/env python3
"""
Detailed test to understand MCP connection issues
"""

import asyncio
import sys
import os
from mcp_servers import fetch_mcp_servers_as_config
from mcp_client.manager import MCPManager

async def test_detailed_mcp():
    print("=== Detailed MCP Connection Test ===")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python executable: {sys.executable}")
    print(f"Python path: {sys.path}")
    
    # Fetch server configuration
    print("\n--- Fetching server configuration ---")
    server_config = fetch_mcp_servers_as_config()
    print(f"Server config: {server_config}")
    
    # Test file existence
    print("\n--- Checking file existence ---")
    for name, config in server_config.items():
        if config.get('transport') == 'stdio' and 'args' in config:
            args = config['args']
            if args and len(args) > 0:
                file_path = args[0]
                exists = os.path.exists(file_path)
                print(f"  {name}: {file_path} - {'EXISTS' if exists else 'NOT FOUND'}")
                if exists:
                    # Check if file is readable
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read(100)  # Read first 100 chars
                            print(f"    First 100 chars: {repr(content[:50])}")
                    except Exception as e:
                        print(f"    Error reading file: {e}")
    
    # Test MCP manager
    print("\n--- Testing MCP Manager ---")
    try:
        manager = MCPManager(server_config)
        print("MCP Manager created successfully")
        
        # Try to get tools
        print("Attempting to fetch tools...")
        tools = await manager.get_tools()
        print(f"Successfully fetched {len(tools)} tools")
        
        # Check connection status
        status = await manager.get_connection_status()
        print(f"Connection status: {status}")
        
    except Exception as e:
        print(f"Error with MCP Manager: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_detailed_mcp())