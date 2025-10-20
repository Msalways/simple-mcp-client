from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from mcp_client.manager import MCPManager
from mcp_servers import fetch_mcp_servers_as_config
from pydantic import SecretStr
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class MCPAgent:
    """Agent that can interact with multiple MCP servers using LangChain."""
    
    def __init__(self):
        print("MCPAgent: Initializing with server config...")
        server_config = fetch_mcp_servers_as_config()
        print(f"MCPAgent: Server config: {server_config}")
        self.client = MCPManager(server_config)
        self.agent = None
    
    async def initialize_agent(self, llm_config: Dict[str, Any]):
        """Initialize the agent with the specified LLM configuration and MCP tools."""
        print(f"MCPAgent: Initializing agent with LLM config: {llm_config}")
        # Create chat model based on configuration
        chat_model = self._create_chat_model(llm_config)
        
        # Get tools from MCP servers
        tools = []
        try:
            print("MCPAgent: Fetching tools from MCP manager...")
            tools = await self.client.get_tools()
            print(f"MCPAgent: Successfully loaded {len(tools)} MCP tools")
        except Exception as e:
            print(f"MCPAgent: Warning: Could not load MCP tools: {e}")
            import traceback
            traceback.print_exc()
            tools = []
        
        # Create LangChain agent with tools (or without if no tools available)
        print("MCPAgent: Creating LangChain agent...")
        self.agent = create_agent(
            model=chat_model,
            tools=tools if tools else None,
            debug=True
        )
        print("MCPAgent: Agent created successfully")
        
        return self
    
    def _create_chat_model(self, config: Dict[str, Any]):
        """Create a chat model based on the configuration."""
        print(f"MCPAgent: Creating chat model with config: {config}")
        # Map provider to model class
        if config['provider'] == 'openai':
            return ChatOpenAI(
                model=config['model'] or "gpt-3.5-turbo",
                api_key=SecretStr(config['api_key']) if config['api_key'] else None,
                base_url=config['base_url'] or "https://api.openai.com/v1"
            )
        elif config['provider'] == 'openrouter':
            return ChatOpenAI(
                model=config['model'] or "openai/gpt-3.5-turbo",
                api_key=SecretStr(config['api_key']) if config['api_key'] else None,
                base_url=config['base_url'] or "https://openrouter.ai/api/v1"
            )
        else:
            raise ValueError(f"Unsupported provider: {config['provider']}")
    
    async def execute(self, input_text: str, chat_history: Optional[List[tuple]] = None) -> str:
        """Execute the agent with the given input and chat history."""
        if not self.agent:
            raise ValueError("Agent not initialized. Call initialize_agent first.")
        
        try:
            print(f"MCPAgent: Executing agent with input: {input_text}")
            # Prepare messages with chat history
            messages = []
            
            # Add chat history to messages
            if chat_history:
                print(f"MCPAgent: Adding chat history: {chat_history}")
                # Convert tuples to message format
                for role, content in chat_history:
                    if role == "human":
                        messages.append({"role": "user", "content": content})
                    elif role == "ai":
                        messages.append({"role": "assistant", "content": content})
            
            # Add the current user message
            messages.append({"role": "user", "content": input_text})
            
            print(f"MCPAgent: Full messages: {messages}")
            # Execute the agent with the messages
            # In LangChain 1.0.0, we pass messages directly
            response = await self.agent.ainvoke({"messages": messages})
            
            # Extract the output content from the response
            result = self._extract_content(response)
            print(f"MCPAgent: Execution result: {result}")
            return result
        except Exception as e:
            print(f"MCPAgent: Error executing agent: {e}")
            import traceback
            traceback.print_exc()
            return f"Error executing agent: {str(e)}"
    
    def _extract_content(self, response) -> str:
        """Extract clean content from various response formats."""
        if isinstance(response, str):
            return response
        elif hasattr(response, 'content'):
            return str(response.content)
        elif isinstance(response, dict):
            # Handle different response formats
            if "output" in response:
                return self._extract_content(response["output"])
            elif "content" in response:
                return self._extract_content(response["content"])
            elif "messages" in response and response["messages"]:
                # Extract content from the last message
                last_message = response["messages"][-1]
                return self._extract_content(last_message)
            else:
                return str(response)
        elif isinstance(response, list) and response:
            # If it's a list, take the last item
            return self._extract_content(response[-1])
        else:
            return str(response)