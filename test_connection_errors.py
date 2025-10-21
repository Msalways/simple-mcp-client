#!/usr/bin/env python3
"""
Test script to simulate and check connection error handling in MCP tools.
This script helps verify that connection closed errors are properly detected and reported.
"""

import asyncio
from chat.agent import MCPAgent
from database import DatabaseManager

async def test_connection_errors():
    """Test connection error handling in MCP agent."""
    print("Testing MCP connection error handling...")
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    # Get existing configurations
    servers = db_manager.get_mcp_servers()
    llm_configs = db_manager.get_llm_configs()
    
    print(f"Found {len(servers)} MCP servers and {len(llm_configs)} LLM configurations")
    
    if not llm_configs:
        print("No LLM configurations found. Please configure an LLM in the Settings tab.")
        return
    
    if not servers:
        print("No MCP servers found. Please configure an MCP server in the Settings tab.")
        return
    
    # Select the first LLM configuration
    llm_config = llm_configs[0]
    print(f"Using LLM configuration: {llm_config['name']} ({llm_config['provider']})")
    
    try:
        # Initialize the MCP agent
        agent = MCPAgent()
        
        # Initialize the agent with the LLM configuration
        print("Initializing agent...")
        await agent.initialize_agent(llm_config)
        
        # Test a simple query
        print("Testing agent execution...")
        response = await agent.execute("Hello, what tools do you have available?", [])
        print(f"Response: {response}")
        
        # Check connection status
        print("Checking connection status...")
        connection_status = await agent.client.get_connection_status()
        print(f"Connection status: {connection_status}")
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection_errors())