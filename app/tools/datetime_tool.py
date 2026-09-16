from datetime import datetime
from zoneinfo import ZoneInfo


def get_current_datetime(timezone: str = "Europe/Dublin") -> str:
    """Return the current date and time for a timezone."""

    try:
        current_time = datetime.now(ZoneInfo(timezone))

        return current_time.strftime(
            "%A, %d %B %Y at %H:%M:%S %Z"
        )

    except Exception:
        return f"Invalid timezone: {timezone}"
