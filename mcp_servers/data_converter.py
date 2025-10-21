from mcp.server.fastmcp import FastMCP
import json

mcp = FastMCP("Data Converter")

@mcp.tool(
    description="Convert a JSON string to a formatted string.",
    structured_output=True,
    title="JSON Formatter Tool",
)
def format_json(json_string: str) -> str:
    """Format a JSON string with indentation."""
    try:
        parsed = json.loads(json_string)
        return json.dumps(parsed, indent=2)
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {str(e)}"

@mcp.tool(
    description="Convert temperature between Celsius and Fahrenheit.",
    structured_output=True,
    title="Temperature Converter Tool",
)
def convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    """Convert temperature between Celsius and Fahrenheit."""
    if from_unit.lower() == "celsius" and to_unit.lower() == "fahrenheit":
        return (value * 9/5) + 32
    elif from_unit.lower() == "fahrenheit" and to_unit.lower() == "celsius":
        return (value - 32) * 5/9
    else:
        return value

@mcp.tool(
    description="Convert a list of items to a comma-separated string.",
    structured_output=True,
    title="List to String Converter Tool",
)
def list_to_string(items: list) -> str:
    """Convert a list of items to a comma-separated string."""
    return ", ".join(str(item) for item in items)

if __name__ == "__main__":
    mcp.run(transport="stdio")