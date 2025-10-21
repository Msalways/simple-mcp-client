#!/usr/bin/env python3
"""
Test script to reproduce the WEATHER tool error and test our human-in-the-loop solution.
"""

import asyncio
import os
from chat.agent import MCPAgent

# LLM config - using the OpenRouter as OpenAI compatible
LLM_CONFIG = {
    'provider': 'openai',  # Using openai since it's OpenRouter as OpenAI
    'model': 'gpt-3.5-turbo',
    'api_key': os.getenv('OPENAI_API_KEY'),
    'base_url': os.getenv('OPENAI_API_BASE')
}

async def test_weather_missing_location():
    """Test the weather tool with missing location parameter."""
    print("Initializing MCP Agent...")
    agent = MCPAgent()

    print("Initializing agent with LLM config...")
    await agent.initialize_agent(LLM_CONFIG)

    print("\nTesting weather query without location...")
    # This should trigger the WEATHER tool but with missing location
    result = await agent.execute("Get me the current weather information.")

    print("\nResponse:")
    print(result)

    print("\nChecking validation failures...")
    failures = agent.validation_callback.get_tool_call_failures()
    print(f"Failures: {failures}")

    if not failures:
        print("\nTesting another query that might trigger tool with missing params...")
        # Try another query that might force tool usage
        result2 = await agent.execute("Call the WEATHERMAP_WEATHER tool.")
        print("\nResponse 2:")
        print(result2)

        print("\nChecking validation failures after second query...")
        failures2 = agent.validation_callback.get_tool_call_failures()
        print(f"Failures after second query: {failures2}")
    else:
        print("Great! We caught validation failures in the first query.")

if __name__ == "__main__":
    asyncio.run(test_weather_missing_location())
