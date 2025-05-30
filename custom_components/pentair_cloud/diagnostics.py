"""Diagnostics support for Pentair."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics.util import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import PentairDataUpdateCoordinator

TO_REDACT = {"arn", "deviceId", "email", "userId"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: PentairDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    diagnostics_data = {
        "get_devices": coordinator.data,
        "get_device": {
            "***" + device_coordinator.device_id[-4:]: device_coordinator.data
            for device_coordinator in coordinator.device_coordinators
        },
    }
    return async_redact_data(diagnostics_data, TO_REDACT)
