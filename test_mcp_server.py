from mcp.server.fastmcp import FastMCP

mcp = FastMCP("TestServer")

@mcp.tool(
    description="Multiply two numbers together and return the result.",
    structured_output=True,
    title="Multiplication Tool",
)
def multiply(x: int, y: int) -> int:
    """Multiply two numbers."""
    return x * y

if __name__ == "__main__":
    mcp.run(transport="stdio")