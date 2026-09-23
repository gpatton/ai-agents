import logging
from typing import Any, Callable, Optional

from langchain_core.callbacks import BaseCallbackHandler


logger = logging.getLogger(__name__)

ToolEventHandler = Callable[[dict[str, Any]], None]


class ToolLoggingCallback(BaseCallbackHandler):
    """Log tool execution and optionally report tool events."""

    def __init__(
        self,
        request_id: str,
        on_event: Optional[ToolEventHandler] = None,
    ):
        super().__init__()
        self.request_id = request_id
        self.on_event = on_event
        self.tool_names: dict[str, str] = {}

    def emit(self, event: dict[str, Any]) -> None:
        if self.on_event is not None:
            self.on_event(
                {
                    "request_id": self.request_id,
                    **event,
                }
            )

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        tool_name = serialized.get("name", "unknown")
        run_id = str(kwargs.get("run_id", ""))

        if run_id:
            self.tool_names[run_id] = tool_name

        logger.info(
            "TOOL START | request_id=%s | tool=%s | input=%s",
            self.request_id,
            tool_name,
            input_str,
        )

        self.emit(
            {
                "type": "tool_start",
                "tool": tool_name,
                "run_id": run_id,
                "input": input_str,
            }
        )

    def on_tool_end(
        self,
        output: Any,
        **kwargs: Any,
    ) -> None:
        run_id = str(kwargs.get("run_id", ""))
        tool_name = self.tool_names.pop(run_id, "unknown")

        logger.info(
            "TOOL END | request_id=%s | output=%s",
            self.request_id,
            output,
        )

        self.emit(
            {
                "type": "tool_end",
                "tool": tool_name,
                "run_id": run_id,
                "output": str(output),
            }
        )

    def on_tool_error(
        self,
        error: BaseException,
        **kwargs: Any,
    ) -> None:
        run_id = str(kwargs.get("run_id", ""))
        tool_name = self.tool_names.pop(run_id, "unknown")

        logger.error(
            "TOOL ERROR | request_id=%s | error=%s",
            self.request_id,
            error,
        )

        self.emit(
            {
                "type": "tool_error",
                "tool": tool_name,
                "run_id": run_id,
                "error": str(error),
            }
        )
