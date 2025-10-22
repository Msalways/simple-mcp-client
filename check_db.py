from database import DatabaseManager
import json

db = DatabaseManager()

# Disable the problematic Weather MCP server
servers = db.get_mcp_servers(enabled_only=False)
for server in servers:
    if server['name'] == 'Weather mcp' and server['enabled']:
        db.update_mcp_server(server['id'], enabled=False)
        print(f'Disabled Weather MCP server (ID: {server["id"]})')

# Get servers again to show current state
servers = db.get_mcp_servers()
print('Enabled MCP Servers in database:')
for server in servers:
    print(f'  {server["name"]}: {json.dumps(server, indent=2)}')

print(f'\nTotal enabled servers: {len(servers)}')

# Also show all servers (enabled and disabled)
all_servers = db.get_mcp_servers(enabled_only=False)
print('\nAll MCP Servers in database (including disabled):')
for server in all_servers:
    status = "DISABLED" if not server['enabled'] else "ENABLED"
    print(f'  {server["name"]} ({status}): {json.dumps(server, indent=2)}')

print(f'\nTotal servers (all): {len(all_servers)}')
