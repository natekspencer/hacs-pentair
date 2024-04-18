"""Helpers."""

from __future__ import annotations

from datetime import datetime
from time import time
from typing import Any

from pypentair.utils import get_api_field_name_and_value

from homeassistant.util.dt import UTC


def convert_timestamp(_ts: float) -> datetime:
    """Convert a timestamp to a datetime."""
    return datetime.fromtimestamp(_ts / (1000 if _ts > time() else 1), UTC)


def get_field_value(key: str, data: dict) -> Any:
    """Get field value."""
    name, value = get_api_field_name_and_value(key, data["fields"][key])
    return value
