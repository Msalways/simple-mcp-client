from mcp.server.fastmcp import FastMCP

mcp = FastMCP("String Utilities")

@mcp.tool(
    description="Reverse a string.",
    structured_output=True,
    title="String Reversal Tool",
)
def reverse_string(text: str) -> str:
    """Reverse the input string."""
    return text[::-1]

@mcp.tool(
    description="Convert a string to uppercase.",
    structured_output=True,
    title="Uppercase Converter Tool",
)
def to_uppercase(text: str) -> str:
    """Convert string to uppercase."""
    return text.upper()

@mcp.tool(
    description="Count the number of characters in a string.",
    structured_output=True,
    title="Character Counter Tool",
)
def count_characters(text: str) -> int:
    """Count the number of characters in a string."""
    return len(text)

if __name__ == "__main__":
    mcp.run(transport="stdio")