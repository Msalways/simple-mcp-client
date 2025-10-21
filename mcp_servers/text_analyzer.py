from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Text Analyzer")

@mcp.tool(
    description="Count the number of words in a text.",
    structured_output=True,
    title="Word Counter Tool",
)
def count_words(text: str) -> int:
    """Count the number of words in a text."""
    return len(text.split())

@mcp.tool(
    description="Count the number of sentences in a text.",
    structured_output=True,
    title="Sentence Counter Tool",
)
def count_sentences(text: str) -> int:
    """Count the number of sentences in a text."""
    import re
    sentences = re.split(r'[.!?]+', text)
    # Filter out empty strings
    sentences = [s for s in sentences if s.strip()]
    return len(sentences)

@mcp.tool(
    description="Find the most common words in a text.",
    structured_output=True,
    title="Common Words Finder Tool",
)
def common_words(text: str, top_n: int = 5) -> list:
    """Find the most common words in a text."""
    import re
    from collections import Counter
    
    # Convert to lowercase and split into words
    words = re.findall(r'\b\w+\b', text.lower())
    
    # Count words and get top N
    word_counts = Counter(words)
    return word_counts.most_common(top_n)

@mcp.tool(
    description="Calculate the reading time of a text (in minutes).",
    structured_output=True,
    title="Reading Time Calculator Tool",
)
def reading_time(text: str, words_per_minute: int = 200) -> float:
    """Calculate the reading time of a text in minutes."""
    word_count = count_words(text)
    return round(word_count / words_per_minute, 2)

if __name__ == "__main__":
    mcp.run(transport="stdio")