from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Calculator")

@mcp.tool(
    description="Subtract two numbers.",
    structured_output=True,
    title="Subtraction Tool",
)
def subtract(x: float, y: float) -> float:
    """Subtract y from x."""
    return x - y

@mcp.tool(
    description="Multiply two numbers.",
    structured_output=True,
    title="Multiplication Tool",
)
def multiply(x: float, y: float) -> float:
    """Multiply two numbers."""
    return x * y

@mcp.tool(
    description="Divide two numbers.",
    structured_output=True,
    title="Division Tool",
)
def divide(x: float, y: float) -> float:
    """Divide x by y."""
    if y == 0:
        raise ValueError("Cannot divide by zero")
    return x / y

@mcp.tool(
    description="Calculate the power of a number.",
    structured_output=True,
    title="Power Tool",
)
def power(base: float, exponent: float) -> float:
    """Raise base to the power of exponent."""
    return base ** exponent

if __name__ == "__main__":
    mcp.run(transport="stdio")