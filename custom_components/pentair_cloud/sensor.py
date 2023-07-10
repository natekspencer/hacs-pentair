"""Support for Pentair sensors."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfMass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.dt import UTC

from .const import DOMAIN
from .entity import PentairDataUpdateCoordinator, PentairEntity


@dataclass
class RequiredKeysMixin:
    """Required keys mixin."""

    value_fn: Callable[[dict], Any]


@dataclass
class PentairSensorEntityDescription(SensorEntityDescription, RequiredKeysMixin):
    """Pentair sensor entity description."""


SENSOR_MAP: dict[str | None, tuple[PentairSensorEntityDescription, ...]] = {
    None: (
        PentairSensorEntityDescription(
            key="last_report",
            device_class=SensorDeviceClass.TIMESTAMP,
            entity_category=EntityCategory.DIAGNOSTIC,
            translation_key="last_report",
            value_fn=lambda data: datetime.fromtimestamp(
                data["lastReport"] / 1000, UTC
            ),
        ),
    ),
    "SSS1": (
        PentairSensorEntityDescription(
            key="average_salt_usage_per_day",
            device_class=SensorDeviceClass.WEIGHT,
            native_unit_of_measurement=UnitOfMass.POUNDS,
            state_class=SensorStateClass.MEASUREMENT,
            translation_key="average_salt_usage_per_day",
            value_fn=lambda data: data["fields"]["average_salt_usage_per_day"],
        ),
        PentairSensorEntityDescription(
            key="battery_level",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:battery",
            translation_key="battery_level",
            value_fn=lambda data: data["fields"]["battery_level"],
        ),
        PentairSensorEntityDescription(
            key="salt_level",
            translation_key="salt_level",
            value_fn=lambda data: data["fields"]["salt_level"],
        ),
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Pentair sensors using config entry."""
    coordinator: PentairDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        PentairSensorEntity(
            coordinator=coordinator,
            config_entry=config_entry,
            description=description,
            device_id=device["deviceId"],
        )
        for device in coordinator.get_devices()
        for device_type, descriptions in SENSOR_MAP.items()
        for description in descriptions
        if device_type is None or device["deviceType"] == device_type
    ]

    if not entities:
        return

    async_add_entities(entities)


class PentairSensorEntity(PentairEntity, SensorEntity):
    """Pentair sensor entity."""

    entity_description: PentairSensorEntityDescription

    @property
    def native_value(self) -> str | int | datetime | None:
        """Return the value reported by the sensor."""
        return self.entity_description.value_fn(self.get_device())
