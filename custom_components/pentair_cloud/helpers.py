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
    return value.get("value", value) if isinstance(value, dict) else value


class _Missing:
    """Placeholder for a key that is absent on one side of a diff."""

    def __repr__(self) -> str:
        return "<missing>"


MISSING = _Missing()


def diff_data(old: Any, new: Any, path: str = "root") -> dict[str, tuple[Any, Any]]:
    """Return `{path: (old, new)}` for each value that differs between two payloads.

    Nested dicts are compared key by key, and a key present on only one side is
    reported as `MISSING` on the other. Other values, including lists, are
    compared as a whole.
    """
    if isinstance(old, dict) and isinstance(new, dict):
        changes: dict[str, tuple[Any, Any]] = {}
        for key in [*old, *(key for key in new if key not in old)]:
            changes |= diff_data(
                old.get(key, MISSING), new.get(key, MISSING), f"{path}[{key!r}]"
            )
        return changes
    return {} if old == new else {path: (old, new)}
