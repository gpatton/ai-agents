import logging
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler


logger = logging.getLogger(__name__)


class ToolLoggingCallback(BaseCallbackHandler):
    """Log tool execution for a single AgentForge request."""

    def __init__(self, request_id: str):
        super().__init__()
        self.request_id = request_id

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        tool_name = serialized.get("name", "unknown")

        logger.info(
            "TOOL START | request_id=%s | tool=%s | input=%s",
            self.request_id,
            tool_name,
            input_str,
        )

    def on_tool_end(
        self,
        output: Any,
        **kwargs: Any,
    ) -> None:
        logger.info(
            "TOOL END | request_id=%s | output=%s",
            self.request_id,
            output,
        )

    def on_tool_error(
        self,
        error: BaseException,
        **kwargs: Any,
    ) -> None:
        logger.error(
            "TOOL ERROR | request_id=%s | error=%s",
            self.request_id,
            error,
        )
