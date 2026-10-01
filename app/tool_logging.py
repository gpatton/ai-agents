
import logging
from time import perf_counter
from typing import Any, Callable, Optional

from langchain_core.callbacks import BaseCallbackHandler


logger = logging.getLogger(__name__)

ToolEventHandler = Callable[[dict[str, Any]], None]


class ToolLoggingCallback(BaseCallbackHandler):
    """Log tool execution, duration, and optionally report tool events."""

    def __init__(
        self,
        request_id: str,
        on_event: Optional[ToolEventHandler] = None,
    ):
        super().__init__()
        self.request_id = request_id
        self.on_event = on_event
        self.tool_names: dict[str, str] = {}
        self.tool_start_times: dict[str, float] = {}

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
            self.tool_start_times[run_id] = perf_counter()

        logger.info(
            "TOOL START | request_id=%s | tool=%s",
            self.request_id,
            tool_name,
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

        start_time = self.tool_start_times.pop(run_id, None)
        duration_ms = (
            round((perf_counter() - start_time) * 1000, 2)
            if start_time is not None
            else None
        )

        logger.info(
            "TOOL END | request_id=%s | tool=%s | duration_ms=%s",
            self.request_id,
            tool_name,
            duration_ms,
        )

        self.emit(
            {
                "type": "tool_end",
                "tool": tool_name,
                "run_id": run_id,
                "output": str(output),
                "duration_ms": duration_ms,
            }
        )

    def on_tool_error(
        self,
        error: BaseException,
        **kwargs: Any,
    ) -> None:
        run_id = str(kwargs.get("run_id", ""))
        tool_name = self.tool_names.pop(run_id, "unknown")

        start_time = self.tool_start_times.pop(run_id, None)
        duration_ms = (
            round((perf_counter() - start_time) * 1000, 2)
            if start_time is not None
            else None
        )

        logger.error(
            "TOOL ERROR | request_id=%s | tool=%s | "
            "error_type=%s | duration_ms=%s",
            self.request_id,
            tool_name,
            type(error).__name__,
            duration_ms,
        )

        self.emit(
            {
                "type": "tool_error",
                "tool": tool_name,
                "run_id": run_id,
                "error": str(error),
                "duration_ms": duration_ms,
            }
        )
