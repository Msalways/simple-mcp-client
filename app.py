import streamlit as st
import sqlite3
from database import DatabaseManager
from chat.agent import MCPAgent
import asyncio
import pandas as pd
import json
from mcp_client.manager import MCPManager

# Initialize database manager
db_manager = DatabaseManager()

# Set up the page configuration
st.set_page_config(
    page_title="MCP Chat Application",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "editing_server" not in st.session_state:
    st.session_state.editing_server = None
if "editing_config" not in st.session_state:
    st.session_state.editing_config = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "Chat"
if "show_mcp_modal" not in st.session_state:
    st.session_state.show_mcp_modal = False
if "show_llm_modal" not in st.session_state:
    st.session_state.show_llm_modal = False
if "add_server_transport" not in st.session_state:
    st.session_state.add_server_transport = "stdio"
if "edit_server_data" not in st.session_state:
    st.session_state.edit_server_data = None
if "edit_config_data" not in st.session_state:
    st.session_state.edit_config_data = None
if "connection_alert" not in st.session_state:
    st.session_state.connection_alert = None

# Sidebar navigation
st.sidebar.title("🤖 MCP Chat Application")

# Navigation buttons in sidebar
if st.sidebar.button("💬 Chat", key="nav_chat", width='stretch'):
    st.session_state.current_page = "Chat"
    
if st.sidebar.button("⚙️ Settings", key="nav_settings", width='stretch'):
    st.session_state.current_page = "Settings"

st.sidebar.markdown("---")

# Get available LLM configurations for the dropdown
llm_configs = db_manager.get_llm_configs()
llm_options = {config['name']: config for config in llm_configs} if llm_configs else {}

async def run_agent(agent: MCPAgent, prompt: str, chat_history, llm_config):
    """Run the MCP agent with the given prompt and chat history."""
    try:
        # Initialize the agent with the LLM configuration
        await agent.initialize_agent(llm_config)
        response = await agent.execute(prompt, chat_history)
        
        # Check if there were connection errors and set alert
        if hasattr(agent, 'connection_errors') and agent.connection_errors:
            st.session_state.connection_alert = "⚠️ Connection issue detected with MCP servers. Only built-in tools are available. Please check your MCP server configurations in the Settings tab."
        
        return response
    except Exception as e:
        error_msg = str(e)
        # Check if the error is related to connection issues
        if "connection" in error_msg.lower() or "closed" in error_msg.lower():
            st.session_state.connection_alert = "⚠️ Connection error detected! Please check your MCP server configurations in the Settings tab."
        return f"Error occurred: {error_msg}"

if st.session_state.current_page == "Chat":
    st.title("💬 Chat")
    st.subheader("Chat with your MCP-enabled AI assistant")
    
    # Display connection alert if there is one
    if st.session_state.connection_alert:
        st.error(st.session_state.connection_alert)
        # Option to dismiss the alert
        if st.button("Dismiss Alert"):
            st.session_state.connection_alert = None
            st.rerun()
    
    # LLM selection dropdown
    if llm_options:
        selected_llm_name = st.selectbox(
            "Select LLM Configuration",
            options=list(llm_options.keys()),
            key="llm_selector"
        )
        selected_llm = llm_options[selected_llm_name]
        st.caption(f"Using {selected_llm['provider']} - {selected_llm['model'] or 'Default Model'}")
    else:
        st.warning("No LLM configurations found. Please add one in Settings.")
        selected_llm = None
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("What would you like to know?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate bot response using MCP agent
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = "Thinking..."
            message_placeholder.markdown(full_response)
            
            if selected_llm:
                try:
                    # Initialize the MCP agent
                    agent = MCPAgent()
                    # Format chat history for the agent
                    chat_history = []
                    for msg in st.session_state.messages[:-1]:  # Exclude the current message
                        if msg["role"] == "user":
                            chat_history.append(("human", msg["content"]))
                        else:
                            chat_history.append(("ai", msg["content"]))
                    
                    # Run the agent
                    full_response = asyncio.run(run_agent(agent, prompt, chat_history, selected_llm))
                except Exception as e:
                    full_response = f"Error occurred: {str(e)}"
                    # Check if the error is related to connection issues
                    error_msg = str(e)
                    if "connection" in error_msg.lower() or "closed" in error_msg.lower():
                        st.session_state.connection_alert = "⚠️ Connection error detected! Please check your MCP server configurations in the Settings tab."
            else:
                full_response = "Please configure an LLM in the Settings tab."
            
            message_placeholder.markdown(full_response)
        
        # Add bot response to chat history
        st.session_state.messages.append({"role": "assistant", "content": full_response})

elif st.session_state.current_page == "Settings":
    st.title("⚙️ Settings")
    
    # Create tabs for different settings
    tab1, tab2 = st.tabs(["MCP Servers", "LLM Configuration"])
    
    with tab1:
        st.header("MCP Server Configuration")
        
        # Display existing MCP servers in a table
        st.subheader("Configured MCP Servers")
        servers = db_manager.get_mcp_servers(enabled_only=False)
        
        if servers:
            # Action buttons for each server
            for i, server in enumerate(servers):
                cols = st.columns([3, 3, 2, 2, 1, 1])
                cols[0].write(server['name'])
                cols[1].write(server['description'] or "")
                cols[2].write(server['transport'])
                cols[3].write("Enabled" if server['enabled'] else "Disabled")
                if cols[4].button("✏️", key=f"edit_server_{server['id']}"):
                    st.session_state.edit_server_data = server
                    st.session_state.show_mcp_modal = "edit"
                    st.rerun()
                if cols[5].button("🗑️", key=f"delete_server_{server['id']}"):
                    db_manager.delete_mcp_server(server['id'])
                    st.success(f"Server '{server['name']}' deleted!")
                    st.rerun()
        else:
            st.info("No MCP servers configured yet.")
        
        # Add new server button
        if st.button("➕ Add New MCP Server"):
            st.session_state.edit_server_data = None
            st.session_state.show_mcp_modal = "add"
            st.rerun()
    
    with tab2:
        st.header("LLM Configuration")
        
        # Display existing LLM configurations in a table
        st.subheader("Configured LLMs")
        configs = db_manager.get_llm_configs(enabled_only=False)
        
        if configs:
            # Action buttons for each configuration
            for i, config in enumerate(configs):
                cols = st.columns([2, 2, 2, 2, 2, 1, 1])
                cols[0].write(config['name'])
                cols[1].write(config['provider'])
                cols[2].write(config['model'] or "Default")
                cols[3].write(config['base_url'] or "Default")
                cols[4].write("Enabled" if config['enabled'] else "Disabled")
                if cols[5].button("✏️", key=f"edit_config_{config['id']}"):
                    st.session_state.edit_config_data = config
                    st.session_state.show_llm_modal = "edit"
                    st.rerun()
                if cols[6].button("🗑️", key=f"delete_config_{config['id']}"):
                    db_manager.delete_llm_config(config['id'])
                    st.success(f"Configuration '{config['name']}' deleted!")
                    st.rerun()
        else:
            st.info("No LLM configurations set up yet.")
        
        # Add new configuration button
        if st.button("➕ Add New LLM Configuration"):
            st.session_state.edit_config_data = None
            st.session_state.show_llm_modal = "add"
            st.rerun()

# Modal for MCP Server Configuration
if st.session_state.show_mcp_modal:
    with st.expander("MCP Server Configuration", expanded=True):
        if st.session_state.show_mcp_modal == "add":
            st.subheader("Add New MCP Server")
        else:
            server_name = ""
            if st.session_state.edit_server_data is not None:
                server_name = st.session_state.edit_server_data.get('name', '')
            st.subheader(f"Edit Server: {server_name}")
        
        # Handle file upload outside the form for add mode
        uploaded_file = None
        file_path = None
        transport = "stdio"  # Default transport
        
        if st.session_state.show_mcp_modal == "add":
            st.subheader("Stdio Transport - Upload Local MCP Server (Optional)")
            uploaded_file = st.file_uploader("Upload Python File", type=["py"], key="mcp_file_uploader_modal")
            
            if uploaded_file is not None:
                st.info("Uploaded files will use 'stdio' transport automatically")
                # Create directory for uploaded servers if it doesn't exist
                import os
                upload_dir = "mcp_servers"
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)
                
                # Save file with original name
                file_path = os.path.join(upload_dir, uploaded_file.name)
                
                # Show the file path that will be used as argument
                st.caption(f"File will be saved to: {file_path}")
                st.caption(f"This path will be used as the argument: ./{file_path}")
                transport = "stdio"
            else:
                # Transport selection outside the form
                transport = st.selectbox(
                    "Transport Type",
                    ["stdio", "streamable_http", "sse"],
                    key="add_server_transport_selector_modal",
                    index=["stdio", "streamable_http", "sse"].index(st.session_state.add_server_transport) if st.session_state.add_server_transport in ["stdio", "streamable_http", "sse"] else 0
                )
                # Update session state
                st.session_state.add_server_transport = transport
        else:
            # Edit mode - transport selection outside the form
            transport_value = "stdio"
            if st.session_state.edit_server_data is not None:
                transport_value = st.session_state.edit_server_data.get('transport', 'stdio')

            default_transport_index = 0
            if transport_value in ["stdio", "streamable_http", "sse"]:
                default_transport_index = ["stdio", "streamable_http", "sse"].index(transport_value)

            transport = st.selectbox(
                "Transport Type",
                ["stdio", "streamable_http", "sse"],
                key="edit_server_transport_selector_modal",
                index=default_transport_index
            )
        
        # Server configuration fields (outside form for Test Connection access)
        if st.session_state.show_mcp_modal == "add":
            name = st.text_input("Server Name")
            description = st.text_area("Description", placeholder="Enter a description for this MCP server (optional)")
        else:
            # Edit mode
            name_value = ""
            description_value = ""

            if st.session_state.edit_server_data is not None:
                name_value = st.session_state.edit_server_data.get('name', '')
                description_value = st.session_state.edit_server_data.get('description', '') or ""

            name = st.text_input("Server Name", value=name_value)
            description = st.text_area("Description", value=description_value, placeholder="Enter a description for this MCP server (optional)")

        # Conditional fields based on transport type
        command = ""
        args = ""
        env = ""
        url = ""

        if transport == "stdio":
            st.subheader("Stdio Transport Configuration")
            if st.session_state.show_mcp_modal == "add" and uploaded_file is not None:
                # For uploaded files, prefill the args with the file path
                command = st.text_input("Command", value="python", disabled=True)
                if file_path is not None:
                    args = st.text_input("Arguments", value=f"./{file_path}", disabled=True)
                else:
                    args = st.text_input("Arguments", value="", disabled=True)
                env = st.text_area("Environment Variables (JSON)", value="", height=100, disabled=True)
                st.caption("Command, arguments, and environment are automatically set for uploaded files")
            else:
                if st.session_state.show_mcp_modal == "edit" and st.session_state.edit_server_data is not None:
                    command_value = st.session_state.edit_server_data.get('command', '') or ""
                    command = st.text_input("Command", value=command_value)
                    args_value = ""
                    if st.session_state.edit_server_data.get('args'):
                        # Args are now always list, so join them
                        if isinstance(st.session_state.edit_server_data['args'], list):
                            args_value = ",".join(st.session_state.edit_server_data['args'])
                        else:
                            args_value = str(st.session_state.edit_server_data['args'])
                    args = st.text_input("Arguments", value=args_value)
                    env_value = ""
                    if st.session_state.edit_server_data.get('env'):
                        # Env is always dict, format as JSON
                        if isinstance(st.session_state.edit_server_data['env'], dict):
                            env_value = json.dumps(st.session_state.edit_server_data['env'], indent=2)
                        else:
                            env_value = "{}"
                    env = st.text_area("Environment Variables (JSON)", value=env_value, height=100)
                else:
                    command = st.text_input("Command", placeholder="e.g., python")
                    args = st.text_input("Arguments", placeholder="e.g., server.py,arg1,arg2")
                    env = st.text_area("Environment Variables (JSON)", value="", height=100, placeholder='{"API_KEY": "your_key"}')
                st.caption("Command to execute the server. Arguments are comma-separated. Environment variables as JSON object.")
        elif transport in ["streamable_http", "sse"]:
            transport_names = {
                "streamable_http": "Streamable HTTP",
                "sse": "Server-Sent Events"
            }
            st.subheader(f"{transport_names[transport]} Transport Configuration")
            # Show URL field, args as comma-separated, env as JSON
            if st.session_state.show_mcp_modal == "edit" and st.session_state.edit_server_data is not None:
                url_value = st.session_state.edit_server_data.get('url', '') or ""
                url = st.text_input("Server URL", value=url_value)
                args_value = ""
                if st.session_state.edit_server_data.get('args'):
                    # Args are now always list, so join them
                    if isinstance(st.session_state.edit_server_data['args'], list):
                        args_value = ",".join(st.session_state.edit_server_data['args'])
                    else:
                        args_value = str(st.session_state.edit_server_data['args'])
                args = st.text_input("Arguments", value=args_value)
                env_value = ""
                if st.session_state.edit_server_data.get('env'):
                    # Env is always dict, format as JSON
                    if isinstance(st.session_state.edit_server_data['env'], dict):
                        env_value = json.dumps(st.session_state.edit_server_data['env'], indent=2)
                    else:
                        env_value = "{}"
                env = st.text_area("Environment Variables (JSON)", value=env_value, height=100)
            else:
                url = st.text_input("Server URL", placeholder=f"e.g., http://localhost:8000/mcp")
                args = st.text_input("Arguments", placeholder="e.g., arg1,arg2")
                env = st.text_area("Environment Variables (JSON)", value="", height=100, placeholder='{"AUTH_TOKEN": "your_token"}')
            st.caption(f"URL where the {transport_names[transport]} server is running. Arguments are comma-separated. Environment variables as JSON for auth or headers.")

        # Enabled checkbox
        enabled_default = True
        if st.session_state.show_mcp_modal == "edit" and st.session_state.edit_server_data is not None:
            enabled_default = bool(st.session_state.edit_server_data.get('enabled', True))
        enabled = st.checkbox("Enabled", value=enabled_default)

        # Test Connection button (outside form, can access field values)
        if st.button("🔗 Test Connection", key="test_connection_button"):
            # Build temporary server config from form values
            temp_config = {}
            temp_name = name if name else "test_server"

            temp_config[temp_name] = {
                "transport": transport,
            }

            # Add transport-specific fields - args are now always comma-separated list for all transports
            if transport == "stdio":
                if command:
                    temp_config[temp_name]["command"] = command
                if args:
                    temp_args = [arg.strip() for arg in args.split(",") if arg.strip()] if args else []
                    if temp_args:
                        temp_config[temp_name]["args"] = temp_args
                # No env for test connection currently
            elif transport in ["streamable_http", "sse"]:
                if url:
                    temp_config[temp_name]["url"] = url
                if args:
                    temp_args = [arg.strip() for arg in args.split(",") if arg.strip()] if args else []
                    if temp_args:
                        temp_config[temp_name]["args"] = temp_args
                # No env for test connection currently

            # Test the connection to this specific server
            try:
                test_manager = MCPManager(temp_config)
                status, details = asyncio.run(test_manager.test_server_connection(temp_name))
                if status == "success":
                    st.success(f"✅ Connection successful! {details}")
                elif status == "no_tools":
                    st.warning(f"⚠️ Connection established but {details}")
                else:
                    st.error(f"❌ Connection failed: {details}")
            except Exception as e:
                st.error(f"❌ Connection test failed: {str(e)}")

        # Form for submit buttons only
        with st.form("mcp_server_form"):
            # Form buttons
            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("Save" if st.session_state.show_mcp_modal == "edit" else "Add Server")
            with col2:
                cancelled = st.form_submit_button("Cancel")

            if submitted:
                if st.session_state.show_mcp_modal == "add":
                    # Initialize args_list and env_dict
                    args_list = []
                    env_dict = {}

                    # Handle uploaded file if present
                    if uploaded_file is not None and file_path is not None:
                        # Save the uploaded file
                        try:
                            with open(file_path, "wb") as f:
                                f.write(uploaded_file.getbuffer())

                            # Set command and args for uploaded file
                            command = "python"
                            args_list = [f"./{file_path}"]
                            env_dict = {}
                        except Exception as e:
                            st.error(f"Failed to save uploaded file: {str(e)}")
                            args_list = []
                            env_dict = {}
                    else:
                        # Parse args as comma-separated list for all transports
                        args_list = [arg.strip() for arg in args.split(",") if arg.strip()] if args else []
                        # Parse env as JSON dict
                        try:
                            env_dict = json.loads(env) if env.strip() else {}
                        except json.JSONDecodeError:
                            st.error("Invalid JSON in Environment Variables field. Please provide valid JSON.")
                            env_dict = {}

                    # Handle optional parameters
                    command_param = command if command else None
                    args_param = args_list if args_list else None
                    env_param = env_dict if env_dict else None
                    url_param = url if url else None
                    description_param = description if description else None

                    if db_manager.add_mcp_server(name, transport, command_param, args_param, env_param, url_param, description_param):
                        st.success(f"Server '{name}' added successfully!")
                        # Reset session state
                        st.session_state.add_server_transport = "stdio"
                        st.session_state.show_mcp_modal = False
                        st.rerun()  # Refresh to show updated list
                    else:
                        st.error(f"Failed to add server '{name}'. It might already exist.")
                else:
                    # Edit mode - same logic as add
                    args_list = [arg.strip() for arg in args.split(",") if arg.strip()] if args else []
                    # Parse env as JSON dict
                    try:
                        env_dict = json.loads(env) if env.strip() else {}
                    except json.JSONDecodeError:
                        st.error("Invalid JSON in Environment Variables field. Please provide valid JSON.")
                        env_dict = {}
                    # Handle optional parameters
                    command_param = command if command else None
                    args_param = args_list if args_list else None
                    env_param = env_dict if env_dict else None
                    url_param = url if url else None
                    description_param = description if description else None

                    if st.session_state.edit_server_data is not None and db_manager.update_mcp_server(
                        st.session_state.edit_server_data['id'],
                        name=name,
                        description=description_param,
                        transport=transport,
                        command=command_param,
                        args=args_param,
                        env=env_param,
                        url=url_param,
                        enabled=enabled
                    ):
                        st.success(f"Server '{name}' updated successfully!")
                        st.session_state.show_mcp_modal = False
                        st.session_state.edit_server_data = None
                        st.rerun()  # Refresh to show updated list
                    else:
                        st.error(f"Failed to update server '{name}'.")

            if cancelled:
                st.session_state.show_mcp_modal = False
                st.session_state.edit_server_data = None
                st.rerun()

# Modal for LLM Configuration
if st.session_state.show_llm_modal:
    with st.expander("LLM Configuration", expanded=True):
        if st.session_state.show_llm_modal == "add":
            st.subheader("Add New LLM Configuration")
        else:
            config_name = ""
            if st.session_state.edit_config_data is not None:
                config_name = st.session_state.edit_config_data.get('name', '')
            st.subheader(f"Edit Configuration: {config_name}")
        
        # Form for LLM configuration
        with st.form("llm_config_form"):
            if st.session_state.show_llm_modal == "add":
                name = st.text_input("Configuration Name")
                provider = st.selectbox("Provider", ["openai", "openrouter"])
                api_key = st.text_input("API Key", type="password")
                model = st.text_input("Model", placeholder="e.g., gpt-3.5-turbo")
                
                if provider == "openrouter":
                    base_url = st.text_input("Base URL", value="https://openrouter.ai/api/v1")
                else:
                    base_url = st.text_input("Base URL", placeholder="Optional")
            else:
                # Edit mode
                name_value = ""
                provider_value = "openai"
                api_key_value = ""
                model_value = ""
                base_url_value = ""
                
                if st.session_state.edit_config_data is not None:
                    name_value = st.session_state.edit_config_data.get('name', '')
                    provider_value = st.session_state.edit_config_data.get('provider', 'openai')
                    api_key_value = st.session_state.edit_config_data.get('api_key', '')
                    model_value = st.session_state.edit_config_data.get('model', '') or ""
                    base_url_value = st.session_state.edit_config_data.get('base_url', '') or ""
                
                name = st.text_input("Configuration Name", value=name_value)
                provider_index = 0
                if provider_value in ["openai", "openrouter"]:
                    provider_index = ["openai", "openrouter"].index(provider_value)
                provider = st.selectbox("Provider", ["openai", "openrouter"], index=provider_index)
                api_key = st.text_input("API Key", value=api_key_value, type="password")
                model = st.text_input("Model", value=model_value)
                
                if provider_value == "openrouter":
                    base_url = st.text_input("Base URL", value=base_url_value or "https://openrouter.ai/api/v1")
                else:
                    base_url = st.text_input("Base URL", value=base_url_value)
            
            # Enabled checkbox
            enabled_default = True
            if st.session_state.show_llm_modal == "edit" and st.session_state.edit_config_data is not None:
                enabled_default = bool(st.session_state.edit_config_data.get('enabled', True))
            enabled = st.checkbox("Enabled", value=enabled_default)
            
            # Form buttons
            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("Save" if st.session_state.show_llm_modal == "edit" else "Add Configuration")
            with col2:
                cancelled = st.form_submit_button("Cancel")
            
            if submitted:
                # Handle optional parameters
                model_param = model if model else None
                base_url_param = base_url if base_url else None
                
                if st.session_state.show_llm_modal == "add":
                    if db_manager.add_llm_config(name, provider, api_key, model_param, base_url_param):
                        st.success(f"LLM configuration '{name}' added successfully!")
                        st.session_state.show_llm_modal = False
                        st.rerun()  # Refresh to show updated list
                    else:
                        st.error(f"Failed to add LLM configuration '{name}'. It might already exist.")
                else:
                    # Edit mode
                    if st.session_state.edit_config_data is not None and db_manager.update_llm_config(
                        st.session_state.edit_config_data['id'],
                        name=name,
                        provider=provider,
                        api_key=api_key,
                        model=model_param,
                        base_url=base_url_param,
                        enabled=enabled
                    ):
                        st.success(f"Configuration '{name}' updated successfully!")
                        st.session_state.show_llm_modal = False
                        st.session_state.edit_config_data = None
                        st.rerun()  # Refresh to show updated list
                    else:
                        st.error(f"Failed to update configuration '{name}'.")
            
            if cancelled:
                st.session_state.show_llm_modal = False
                st.session_state.edit_config_data = None
                st.rerun()
