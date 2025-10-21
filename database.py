import sqlite3
import os
import json
from typing import List, Dict, Optional, Any

class DatabaseManager:
    def __init__(self, db_path: str = "mcp_config.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create MCP servers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mcp_servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                transport TEXT NOT NULL,
                command TEXT,
                args TEXT,
                url TEXT,
                enabled BOOLEAN DEFAULT 1
            )
        ''')
        
        # Create LLM configurations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS llm_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                provider TEXT NOT NULL,
                api_key TEXT NOT NULL,
                model TEXT,
                base_url TEXT,
                enabled BOOLEAN DEFAULT 1
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_mcp_server(self, name: str, transport: str, command: Optional[str] = None,
                      args: Optional[Any] = None, url: Optional[str] = None,
                      description: Optional[str] = None) -> bool:
        """Add a new MCP server configuration."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Convert args to JSON string for storage
            args_str = json.dumps(args) if args is not None else None

            cursor.execute('''
                INSERT INTO mcp_servers (name, description, transport, command, args, url)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, description, transport, command, args_str, url))

            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            # Server with this name already exists
            return False
        except Exception:
            return False
    
    def get_mcp_servers(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """Retrieve all MCP server configurations."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if enabled_only:
            cursor.execute('SELECT * FROM mcp_servers WHERE enabled = 1')
        else:
            cursor.execute('SELECT * FROM mcp_servers')

        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]

        servers = []
        for row in rows:
            server = dict(zip(columns, row))
            # Convert args JSON string back to original format
            if server['args']:
                try:
                    server['args'] = json.loads(server['args'])
                except (json.JSONDecodeError, TypeError):
                    # If parsing fails, keep as string
                    pass
            servers.append(server)

        conn.close()
        return servers
    
    def update_mcp_server(self, server_id: int, **kwargs) -> bool:
        """Update an existing MCP server configuration."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Build dynamic update query
            fields = []
            values = []
            for key, value in kwargs.items():
                if key in ['name', 'description', 'transport', 'command', 'args', 'url', 'enabled']:
                    fields.append(f"{key} = ?")
                    # Convert args to JSON string for storage
                    if key == 'args':
                        value = json.dumps(value) if value is not None else None
                    values.append(value)

            if not fields:
                return False

            values.append(server_id)
            query = f"UPDATE mcp_servers SET {', '.join(fields)} WHERE id = ?"

            cursor.execute(query, values)
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False
    
    def delete_mcp_server(self, server_id: int) -> bool:
        """Delete an MCP server configuration."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM mcp_servers WHERE id = ?', (server_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False
    
    def add_llm_config(self, name: str, provider: str, api_key: str, 
                      model: Optional[str] = None, base_url: Optional[str] = None) -> bool:
        """Add a new LLM configuration."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO llm_configs (name, provider, api_key, model, base_url)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, provider, api_key, model, base_url))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            # Config with this name already exists
            return False
        except Exception:
            return False
    
    def get_llm_configs(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """Retrieve all LLM configurations."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if enabled_only:
            cursor.execute('SELECT * FROM llm_configs WHERE enabled = 1')
        else:
            cursor.execute('SELECT * FROM llm_configs')
        
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        
        configs = []
        for row in rows:
            config = dict(zip(columns, row))
            configs.append(config)
        
        conn.close()
        return configs
    
    def update_llm_config(self, config_id: int, **kwargs) -> bool:
        """Update an existing LLM configuration."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build dynamic update query
            fields = []
            values = []
            for key, value in kwargs.items():
                if key in ['name', 'provider', 'api_key', 'model', 'base_url', 'enabled']:
                    fields.append(f"{key} = ?")
                    values.append(value)
            
            if not fields:
                return False
                
            values.append(config_id)
            query = f"UPDATE llm_configs SET {', '.join(fields)} WHERE id = ?"
            
            cursor.execute(query, values)
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False
    
    def delete_llm_config(self, config_id: int) -> bool:
        """Delete an LLM configuration."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM llm_configs WHERE id = ?', (config_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False