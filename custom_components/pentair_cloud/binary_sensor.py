"""Support for Pentair binary sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import PentairDataUpdateCoordinator, PentairEntity
from .helpers import get_field_value


@dataclass
class RequiredKeysMixin:
    """Required keys mixin."""

    is_on: Callable[[dict], bool]


@dataclass
class PentairBinarySensorEntityDescription(
    BinarySensorEntityDescription, RequiredKeysMixin
):
    """Pentair binary sensor entity description."""


SENSOR_MAP: dict[str | None, tuple[PentairBinarySensorEntityDescription, ...]] = {
    "IF31": (
        PentairBinarySensorEntityDescription(
            key="pump_enabled",
            translation_key="pump_enabled",
            is_on=lambda data: get_field_value("s25", data),
        ),
    ),
    "PPA0": (
        PentairBinarySensorEntityDescription(
            key="low_battery",
            device_class=BinarySensorDeviceClass.BATTERY,
            entity_category=EntityCategory.DIAGNOSTIC,
            translation_key="low_battery",
            is_on=lambda data: int(data["fields"]["bvl"]) < 3
            or data["fields"]["bft"] == "4",
        ),
        PentairBinarySensorEntityDescription(
            key="battery_charging",
            device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
            entity_category=EntityCategory.DIAGNOSTIC,
            is_on=lambda data: data["fields"]["bch"] != "2",
        ),
        PentairBinarySensorEntityDescription(
            key="online",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
            entity_category=EntityCategory.DIAGNOSTIC,
            translation_key="online",
            is_on=lambda data: data["fields"]["online"],
        ),
        PentairBinarySensorEntityDescription(
            key="power",
            device_class=BinarySensorDeviceClass.POWER,
            entity_category=EntityCategory.DIAGNOSTIC,
            translation_key="power",
            is_on=lambda data: data["fields"]["acp"] == "1",
        ),
        PentairBinarySensorEntityDescription(
            key="primary_pump",
            device_class=BinarySensorDeviceClass.PROBLEM,
            translation_key="primary_pump",
            is_on=lambda data: data["fields"]["sts"] == "2",
        ),
        PentairBinarySensorEntityDescription(
            key="secondary_pump",
            device_class=BinarySensorDeviceClass.PROBLEM,
            translation_key="secondary_pump",
            is_on=lambda data: int(data["fields"]["sts"]) > 0,
        ),
        PentairBinarySensorEntityDescription(
            key="water_level",
            device_class=BinarySensorDeviceClass.PROBLEM,
            translation_key="water_level",
            is_on=lambda data: data["fields"]["sts"] == 5,
        ),
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Pentair binary sensors using config entry."""
    coordinator: PentairDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        PentairBinarySensorEntity(
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


class PentairBinarySensorEntity(PentairEntity, BinarySensorEntity):
    """Pentair binary sensor entity."""

    entity_description: PentairBinarySensorEntityDescription

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self.entity_description.is_on(self.get_device())
