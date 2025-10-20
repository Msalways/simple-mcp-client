from langchain_openai import ChatOpenAI
from langchain.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
from database import DatabaseManager
from pydantic import SecretStr
from typing import Optional
import os

load_dotenv()

class LLMWrapper:
    """LLM wrapper that maintains chat history and integrates with database configurations."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager or DatabaseManager()
        self.chat_history = []  # Local array to maintain chat history
    
    def get_llm_config(self, config_name: str):
        """Retrieve LLM configuration by name from database."""
        configs = self.db_manager.get_llm_configs()
        for config in configs:
            if config['name'] == config_name:
                return config
        return None
    
    def create_chat_model(self, config_name: str):
        """Create a chat model based on the configuration from database."""
        config = self.get_llm_config(config_name)
        if not config:
            raise ValueError(f"LLM configuration '{config_name}' not found")
        
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
    
    def add_to_history(self, role: str, content: str | list[str | dict]):
        """Add a message to the chat history."""
        # Handle list content by converting to string
        if isinstance(content, list):
            # Convert list to a string representation
            content_str = " ".join(str(item) for item in content)
        else:
            content_str = content
            
        if role == "user":
            self.chat_history.append(HumanMessage(content=content_str))
        elif role == "assistant":
            self.chat_history.append(AIMessage(content=content_str))
    
    def get_chat_history(self):
        """Get the current chat history."""
        return self.chat_history
    
    def clear_history(self):
        """Clear the chat history."""
        self.chat_history = []
    
    def chat(self, config_name: str, message: str) -> str | list[str | dict]:
        """Send a message to the LLM and get a response."""
        # Add user message to history
        self.add_to_history("user", message)
        
        # Create chat model
        chat_model = self.create_chat_model(config_name)
        
        # Get response from model
        response = chat_model.invoke(self.chat_history)
        
        # Add AI response to history
        self.add_to_history("assistant", response.content)
        
        return response.content