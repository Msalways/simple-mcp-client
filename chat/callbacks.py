from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import BaseMessage
from typing import Any, Dict, List, Union
import asyncio
import re

class StreamPrinter(AsyncCallbackHandler):
    """Callback handler that prints to stdout."""

    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        print(token, end="", flush=True)

    async def on_llm_end(self, response, **kwargs) -> None:
        print("\n --Stream end-- \n")

class ToolValidationCallback(AsyncCallbackHandler):
    """Callback handler that validates tool calls and prompts for missing parameters."""

    def __init__(self, user_prompt_func=None):
        """
        Initialize with a function to prompt the user for missing parameters.

        Args:
            user_prompt_func: Async function that takes a list of missing params and returns a dict of values.
                            Signature: async def prompt_func(missing_params: List[str]) -> Dict[str, Any]
        """
        super().__init__()
        self.user_prompt_func = user_prompt_func
        self.tool_call_failures = {}

    async def on_tool_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> Any:
        """Handle tool execution errors, particularly validation errors."""
        error_str = str(error)

        # Check if this is a validation error (missing required fields)
        if "Field required" in error_str or "missing" in error_str.lower() and ("location" in error_str.lower() or "required" in error_str.lower()):
            # Extract missing fields from the error message
            missing_fields = self._extract_missing_fields(error_str)
            if missing_fields:
                print(f"ToolValidationCallback: Detected missing parameters: {missing_fields}")
                print(f"ToolValidationCallback: Full error: {error_str}")
                self.tool_call_failures[kwargs.get('run_id', 'unknown')] = {
                    'missing_params': missing_fields,
                    'error': error_str,
                    'tool_name': kwargs.get('name', 'unknown')
                }

        # Return the error to continue normal flow - it will be handled upstream
        return error

    def _extract_missing_fields(self, error_msg: str) -> List[str]:
        """Extract missing field names from validation error messages."""
        missing_fields = []

        # Common patterns in validation errors
        patterns = [
            r"Field required\s*\n([^']+)'",  # Pydantic style: Field required\nlocation
            r"missing.*?'([^']+)'",  # missing 'location'
            r"'([^']+)'\s*\n\s*Field required",  # 'location'\nField required
        ]

        for pattern in patterns:
            matches = re.findall(pattern, error_msg, re.IGNORECASE | re.MULTILINE)
            missing_fields.extend(matches)

        return list(set(missing_fields))  # Remove duplicates

    def get_tool_call_failures(self) -> Dict[str, Any]:
        """Get recorded tool call failures."""
        return self.tool_call_failures

    def clear_failures(self):
        """Clear recorded failures."""
        self.tool_call_failures.clear()
