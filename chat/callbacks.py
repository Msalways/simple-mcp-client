from langchain_core.callbacks import AsyncCallbackHandler

class StreamPrinter(AsyncCallbackHandler):
    """Callback handler that prints to stdout."""

    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        print(token, end="", flush=True)
        
    async def on_llm_end(self, response, **kwargs) -> None:
        print("\n --Stream end-- \n")