"""Helpers."""

from __future__ import annotations

from datetime import datetime
import logging
from time import time
from typing import Any

from pypentair.utils import get_api_field_name_and_value

from homeassistant.util.dt import UTC

_LOGGER = logging.getLogger(__name__)


def convert_timestamp(_ts: float) -> datetime:
    """Convert a timestamp to a datetime."""
    return datetime.fromtimestamp(_ts / (1000 if _ts > time() else 1), UTC)


def get_field_value(key: str, data: dict) -> Any:
    """Get field value."""
    name, value = get_api_field_name_and_value(key, data["fields"].get(key))
    if key not in data["fields"]:
        _LOGGER.warning('%s key "%s" is missing in fields data', name, key)
    return value.get("value", value)
