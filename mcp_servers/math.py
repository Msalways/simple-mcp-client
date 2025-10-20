from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Math")

@mcp.tool(
    description="Add two numbers together and return the result.",
    structured_output=True,
    title="Addition Tool",
)
def add(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y

if __name__ == "__main__":
    mcp.run(transport="stdio")
