"""Pentair coordinator."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from deepdiff import DeepDiff
from pypentair import Pentair

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
UPDATE_INTERVAL = 30


class PentairDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, client: Pentair) -> None:
        """Initialize."""
        self.api = client
        self.devices: dict[str, list[dict[str, Any]]] = {}

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    def get_device(self, device_id: str) -> dict | None:
        """Get device by id."""
        return next(
            (
                device
                for device in self.devices.get("data", [])
                if device["deviceId"] == device_id
            ),
            None,
        )

    def get_devices(self, device_type: str | None = None) -> list[dict]:
        """Get device by id."""
        return [
            device
            for device in self.devices.get("data", [])
            if device_type is None or device["deviceType"] == device_type
        ]

    def _normalize_fields(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Normalize field data from detailed API response.

        The get_device API returns full field objects like:
          {"s17": {"name": "...", "value": "436", ...}}
        But existing pypentair code and sensors expect just:
          {"s17": "436"}
        """
        normalized = {}
        for key, value in fields.items():
            if isinstance(value, dict) and "value" in value:
                # Extract just the value string for pypentair compatibility
                normalized[key] = value["value"]
            else:
                # Keep as-is if not a dict or no "value" key
                normalized[key] = value
        return normalized

    async def _async_update_data(self):
        """Update data via library, refresh token if necessary."""
        try:
            # Get list of devices
            devices_response = await self.hass.async_add_executor_job(self.api.get_devices)
            if not devices_response:
                return self.devices

            # Fetch detailed data for each device (includes fields with program info)
            detailed_devices = []
            for device in devices_response.get("data", []):
                device_id = device.get("deviceId")
                if device_id:
                    try:
                        detailed = await self.hass.async_add_executor_job(
                            self.api.get_device, device_id
                        )
                        if detailed and "data" in detailed:
                            device_data = detailed["data"]
                            # Normalize the fields to match expected format
                            if "fields" in device_data:
                                device_data["fields"] = self._normalize_fields(
                                    device_data["fields"]
                                )
                            # Merge detailed data INTO original device to preserve
                            # fields like lastReport that only exist in get_devices()
                            merged_device = {**device, **device_data}
                            detailed_devices.append(merged_device)
                        else:
                            detailed_devices.append(device)
                    except Exception:  # pylint: disable=broad-except
                        _LOGGER.warning("Failed to get detailed data for %s", device_id)
                        detailed_devices.append(device)

            devices = {"data": detailed_devices, "msgs": devices_response.get("msgs", [])}
            diff = DeepDiff(
                self.devices,
                devices,
                ignore_order=True,
                report_repetition=True,
                verbose_level=2,
            )
            _LOGGER.debug("Devices updated: %s", diff if diff else "no changes")
            self.devices = devices
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error(
                "Unknown exception while updating Pentair data: %s", err, exc_info=1
            )
            raise UpdateFailed(err) from err
        return self.devices
