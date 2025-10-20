
from chat.llm import create_mcp_agent


def extract_llm_data(response):
    """Extract relevant data from the LLM response dict."""
    messages = response['messages']
    final_msg = messages[-1]  # The AIMessage

    token_usage = final_msg.response_metadata.get('token_usage', {})
    usage_metadata = getattr(final_msg, 'usage_metadata', {}) or final_msg.response_metadata.get('usage_metadata', {})

    data = {
        'content': final_msg.content,
        'model_name': final_msg.response_metadata.get('model_name'),
        'finish_reason': final_msg.response_metadata.get('finish_reason'),
        'generation_id': final_msg.response_metadata.get('id'),
        'tool_calls': getattr(final_msg, 'tool_calls', []) or [],
        'token_usage': {
            'prompt_tokens': token_usage.get('prompt_tokens'),
            'completion_tokens': token_usage.get('completion_tokens'),
            'total_tokens': token_usage.get('total_tokens')
        },
        'usage_metadata': {
            'input_tokens': usage_metadata.get('input_tokens'),
            'output_tokens': usage_metadata.get('output_tokens'),
            'total_tokens': usage_metadata.get('total_tokens')
        }
    }
    return data


async def chat_loop():
    agent = await create_mcp_agent()
    print("Welcome to the MCP Chat! Type 'exit' to quit.")
    
    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            print("Goodbye!")
            break
        
        response = await agent.ainvoke({
            "messages": [{"role": "user", "content": user_input}]
        })
        data = extract_llm_data(response)
        print(f"Assistant: {data['content']}")
        if data['tool_calls']:
            print(f"Tool calls: {[tc['name'] + f'({tc.get("args", {})})' for tc in data['tool_calls']][:3]}")  # Limit to 3 for brevity
        print(f"Model: {data['model_name']} | Tokens: {data['token_usage']['total_tokens']}")
        
if __name__ == "__main__":
    import asyncio
    asyncio.run(chat_loop())
