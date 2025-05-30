"""Pentair entities."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PentairDeviceDataUpdateCoordinator


class PentairEntity(CoordinatorEntity[PentairDeviceDataUpdateCoordinator]):
    """Base class for Pentair entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PentairDeviceDataUpdateCoordinator,
        config_entry: ConfigEntry,
        description: EntityDescription,
        device_id: str,
    ) -> None:
        """Construct a PentairEntity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self.entity_description = description
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}-{description.key}"

        device = self.get_device()
        info = device["productInfo"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            manufacturer=info.get("maker"),
            model=device["pname"]
            + (f" ({model})" if (model := info.get("model")) else ""),
            name=info["nickName"],
            sw_version=device.get("fwVersion"),
        )

    def get_device(self) -> Any | None:
        """Get the device from the coordinator."""
        return self.coordinator.get_device_data()
