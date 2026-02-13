"""Diagnostics support for Pentair."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics.util import async_redact_data
from homeassistant.core import HomeAssistant

from . import PentairConfigEntry

TO_REDACT = {}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: PentairConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return async_redact_data(entry.runtime_data.data, TO_REDACT)
