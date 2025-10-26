from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from mcp_client.manager import MCPManager
from mcp_servers import fetch_mcp_servers_as_config
from chat.callbacks import ToolValidationCallback
from pydantic import SecretStr
import os
from typing import List, Dict, Any, Optional, cast
from dotenv import load_dotenv
from database import DatabaseManager

load_dotenv()

class MCPAgent:
    """Agent that can interact with multiple MCP servers using LangChain."""
    
    # Class variables to cache tools and resources
    _cached_tools = None
    _cached_resources = None
    _cached_client = None
    _cached_server_info = None
    
    def __init__(self):
        print("MCPAgent: Initializing with server config...")
        server_config = fetch_mcp_servers_as_config()
        print(f"MCPAgent: Server config: {server_config}")
        self.client = MCPManager(cast(Dict[str, Any], server_config))
        self.agent = None
        self.tools = []
    
    async def initialize_agent(self, llm_config: Dict[str, Any]):
        """Initialize the agent with the specified LLM configuration and MCP tools."""
        print(f"MCPAgent: Initializing agent with LLM config: {llm_config}")
        # Create chat model based on configuration
        chat_model = self._create_chat_model(llm_config)
        
        # Get tools from MCP servers with individual failure handling
        self.tools = []
        connection_errors = []
        failed_servers = {}
        resources = []
        server_info = {}
        
        # Get server information from database for descriptions
        db_manager = DatabaseManager()
        db_servers = db_manager.get_mcp_servers(enabled_only=True)
        server_descriptions = {server['name']: server['description'] for server in db_servers}
        
        # Check if we have cached tools and resources
        if (MCPAgent._cached_tools is not None and 
            MCPAgent._cached_resources is not None and 
            MCPAgent._cached_server_info is not None):
            print("MCPAgent: Using cached tools, resources, and server info")
            self.tools = MCPAgent._cached_tools
            resources = MCPAgent._cached_resources
            server_info = MCPAgent._cached_server_info
        else:
            try:
                print("MCPAgent: Fetching tools from MCP manager with failure handling...")
                result = await self.client.get_tools_with_failures()
                if len(result) == 3:
                    self.tools, failed_servers, resources = result
                else:
                    # Handle case where only tools and resources are returned
                    self.tools, resources = result[0], result[1]
                    failed_servers = {}
                print(f"MCPAgent: Successfully loaded {len(self.tools)} MCP tools")
                
                # Create server information with tools mapping
                server_info = {}
                # Group tools by server (this is a simplified approach)
                for server_name in self.client.client.connections.keys():
                    if server_name not in failed_servers:
                        # Get tools for this server
                        server_tools = [tool for tool in self.tools if hasattr(tool, 'name')]
                        server_info[server_name] = {
                            'description': server_descriptions.get(server_name, ''),
                            'tools': server_tools
                        }
                
                # Cache the tools, resources, and server info for future use
                MCPAgent._cached_tools = self.tools
                MCPAgent._cached_resources = resources
                MCPAgent._cached_server_info = server_info
                MCPAgent._cached_client = self.client

                # Convert failed servers to connection errors for backward compatibility
                for server_name, error_msg in failed_servers.items():
                    connection_errors.append(f"Server '{server_name}' failed: {error_msg}")

            except Exception as e:
                error_msg = str(e)
                print(f"MCPAgent: Warning: Could not load MCP tools: {error_msg}")
                import traceback
                traceback.print_exc()
                self.tools = []

                # Check if this is a connection closed error
                if "Connection closed" in error_msg or "connection closed" in error_msg.lower():
                    connection_errors.append(f"Connection closed error: {error_msg}")

        # Create the tool validation callback
        self.validation_callback = ToolValidationCallback()

        # Get system instructions from database
        system_instructions = db_manager.get_system_instructions()
        
        # Create enhanced system prompt with server and tool information
        enhanced_system_prompt = self._create_enhanced_system_prompt(
            system_instructions, 
            server_info, 
            self.tools, 
            resources
        )
        
        # Create LangChain agent with tools and callbacks
        print("MCPAgent: Creating LangChain agent...")
        agent_kwargs = {
            "model": chat_model,
            "tools": self.tools if self.tools else None,
            "debug": True
        }
        
        # Add enhanced system prompt
        if enhanced_system_prompt:
            agent_kwargs["system_prompt"] = enhanced_system_prompt
            
        self.agent = create_agent(**agent_kwargs)

        print("MCPAgent: Agent created successfully")

        # Store connection errors for later use
        self.connection_errors = connection_errors

        return self
    
    def _create_enhanced_system_prompt(self, base_instructions: Optional[str], 
                                     server_info: Dict[str, Any], 
                                     tools: List[Any], 
                                     resources: List[Any]) -> str:
        """Create an enhanced system prompt that includes server descriptions and tool information."""
        prompt_parts = []
        
        # Add base instructions if available
        if base_instructions:
            prompt_parts.append(base_instructions)
        else:
            prompt_parts.append("You are a helpful AI assistant with access to various tools.")
        
        # Add server information
        if server_info:
            prompt_parts.append("\nAVAILABLE TOOL SERVERS:")
            for server_name, info in server_info.items():
                description = info.get('description', '')
                if description:
                    prompt_parts.append(f"- {server_name}: {description}")
                else:
                    prompt_parts.append(f"- {server_name}")
        
        # Add tool information (limit to avoid context window issues)
        if tools:
            prompt_parts.append("\nAVAILABLE TOOLS (use these appropriately based on the server they belong to):")
            # Limit the number of tools to avoid context window issues
            max_tools_to_show = 50  # Adjust based on model context window
            for i, tool in enumerate(tools[:max_tools_to_show]):
                if hasattr(tool, 'name') and hasattr(tool, 'description'):
                    prompt_parts.append(f"- {tool.name}: {tool.description}")
            
            # If we have more tools than the limit, indicate that
            if len(tools) > max_tools_to_show:
                prompt_parts.append(f"... and {len(tools) - max_tools_to_show} more tools available.")
        
        # Add resource information if available
        if resources:
            prompt_parts.append(f"\nAVAILABLE RESOURCES: {len(resources)} resources available.")
        
        # Add guidance on tool selection
        prompt_parts.append("\nIMPORTANT GUIDELINES:")
        prompt_parts.append("- Choose the most appropriate tool based on the server it belongs to")
        prompt_parts.append("- Only use tools that are relevant to the user's request")
        prompt_parts.append("- If you're unsure which tool to use, ask for clarification")
        prompt_parts.append("- Provide clear explanations for your actions")
        
        return "\n".join(prompt_parts)
    
    def _create_chat_model(self, config: Dict[str, Any]):
        """Create a chat model based on the configuration."""
        # print(f"MCPAgent: Creating chat model with config: {config}")
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
            # Clear previous validation failures
            self.validation_callback.clear_failures()

            # Execute the agent with the messages and callbacks
            # In LangChain 1.0.0, we pass messages directly and include callbacks
            response = await self.agent.ainvoke(
                {"messages": messages},
                {"callbacks": [self.validation_callback]}
            )

            # Check for validation failures that may need user input
            validation_failures = self.validation_callback.get_tool_call_failures()
            if validation_failures:
                print(f"MCPAgent: Validation failures detected: {validation_failures}")
                # Return a special response indicating missing parameters
                missing_params_info = []
                for run_id, failure_info in validation_failures.items():
                    missing_params = failure_info.get('missing_params', [])
                    tool_name = failure_info.get('tool_name', 'Unknown tool')
                    if missing_params:
                        missing_params_info.append(f"Tool '{tool_name}' needs: {', '.join(missing_params)}")

                if missing_params_info:
                    error_msg = f"⚠️ The AI attempted to use tools but couldn't provide required parameters. Please provide the missing information:\n" + "\n".join(missing_params_info)
                    error_msg += "\n\n💡 Tip: Try asking more specifically, e.g., 'What's the weather in Bangalore?' instead of just 'What's the weather?'"
                    return error_msg

            # Extract the output content from the response
            result = self._extract_content(response)
            print(f"MCPAgent: Execution result: {result}")

            # If we had connection errors, append a detailed note to the result
            if hasattr(self, 'connection_errors') and self.connection_errors:
                failed_server_names = [error.split("'")[1] for error in self.connection_errors if "'" in error]
                if failed_server_names:
                    error_note = f"\n\n⚠️ Note: The following MCP servers failed to load: {', '.join(failed_server_names)}. Proceeding with available tools only."
                else:
                    error_note = "\n\n⚠️ Note: Some MCP server connections encountered issues. Proceeding with available tools only."
                result += error_note

            return result
        except Exception as e:
            print(f"MCPAgent: Error executing agent: {e}")
            import traceback
            traceback.print_exc()
            
            # Check connection status when we get an error
            try:
                connection_status = await self.client.get_connection_status()
                connection_errors = []
                for name, status in connection_status.items():
                    if status != "Active" or "Error" in str(status):
                        connection_errors.append(f"Server '{name}' connection issue: {status}")
                
                if connection_errors:
                    error_msg = f"Connection errors detected: {', '.join(connection_errors)}. "
                    error_msg += "Please check your MCP server configurations in the Settings tab."
                    print(f"MCPAgent: {error_msg}")
                    return f"Error executing agent: {str(e)}. {error_msg}"
            except Exception as status_error:
                print(f"MCPAgent: Error checking connection status: {status_error}")
            
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
    
    @classmethod
    def clear_cache(cls):
        """Clear the cached tools and resources."""
        cls._cached_tools = None
        cls._cached_resources = None
        cls._cached_server_info = None
        cls._cached_client = None