import asyncio
from chat.agent import MCPAgent

async def test():
    agent = MCPAgent()
    await agent.initialize_agent({
        'provider': 'openai',
        'model': 'gpt-3.5-turbo',
        'api_key': 'test',
        'base_url': 'https://api.openai.com/v1'
    })
    print('Agent initialized successfully')

if __name__ == "__main__":
    asyncio.run(test())
