from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from mcp_client.manager import MCPManager
from mcp_servers import fetch_mcp_servers_as_config
from chat.callbacks import ToolValidationCallback
from pydantic import SecretStr
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Remove unused imports
# from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
# from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

class MCPAgent:
    """Agent that can interact with multiple MCP servers using LangChain."""
    
    def __init__(self):
        print("MCPAgent: Initializing with server config...")
        server_config = fetch_mcp_servers_as_config()
        print(f"MCPAgent: Server config: {server_config}")
        self.client = MCPManager(server_config)
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
        try:
            print("MCPAgent: Fetching tools from MCP manager with failure handling...")
            self.tools, failed_servers = await self.client.get_tools_with_failures()
            print(f"MCPAgent: Successfully loaded {len(self.tools)} MCP tools")

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

        # Create LangChain agent with tools and callbacks
        print("MCPAgent: Creating LangChain agent...")
        self.agent = create_agent(
            model=chat_model,
            tools=self.tools if self.tools else None,
            debug=True
        )

        print("MCPAgent: Agent created successfully")

        # Store connection errors for later use
        self.connection_errors = connection_errors

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