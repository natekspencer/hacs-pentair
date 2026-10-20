"""Support for Pentair binary sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import PentairConfigEntry
from .entity import PentairEntity
from .helpers import get_field_value


@dataclass(frozen=True, kw_only=True)
class PentairBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Pentair binary sensor entity description."""

    is_on: Callable[[dict], bool]


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
            is_on=lambda data: (
                int(get_field_value("bvl", data)) < 3
                or get_field_value("bft", data) == "4"
            ),
        ),
        PentairBinarySensorEntityDescription(
            key="battery_charging",
            device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
            entity_category=EntityCategory.DIAGNOSTIC,
            is_on=lambda data: get_field_value("bch", data) != "2",
        ),
        PentairBinarySensorEntityDescription(
            key="online",
            device_class=BinarySensorDeviceClass.CONNECTIVITY,
            entity_category=EntityCategory.DIAGNOSTIC,
            translation_key="online",
            is_on=lambda data: get_field_value("online", data),
        ),
        PentairBinarySensorEntityDescription(
            key="power",
            device_class=BinarySensorDeviceClass.POWER,
            entity_category=EntityCategory.DIAGNOSTIC,
            translation_key="power",
            is_on=lambda data: get_field_value("acp", data) == "1",
        ),
        PentairBinarySensorEntityDescription(
            key="primary_pump",
            device_class=BinarySensorDeviceClass.PROBLEM,
            translation_key="primary_pump",
            is_on=lambda data: get_field_value("sts", data) == "2",
        ),
        PentairBinarySensorEntityDescription(
            key="secondary_pump",
            device_class=BinarySensorDeviceClass.PROBLEM,
            translation_key="secondary_pump",
            is_on=lambda data: int(get_field_value("sts", data)) > 0,
        ),
        PentairBinarySensorEntityDescription(
            key="water_level",
            device_class=BinarySensorDeviceClass.PROBLEM,
            translation_key="water_level",
            is_on=lambda data: int(get_field_value("sts", data)) == 5,
        ),
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: PentairConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Pentair binary sensors using config entry."""
    coordinator = config_entry.runtime_data

    entities = [
        PentairBinarySensorEntity(
            coordinator=device_coordinator,
            config_entry=config_entry,
            description=description,
            device_id=data["deviceId"],
        )
        for device_coordinator in coordinator.device_coordinators
        if (data := device_coordinator.get_device_data())
        for device_type, descriptions in SENSOR_MAP.items()
        for description in descriptions
        if device_type is None or data["deviceType"] == device_type
    ]

    if not entities:
        return

    async_add_entities(entities)


class PentairBinarySensorEntity(PentairEntity, BinarySensorEntity):
    """Pentair binary sensor entity."""

    entity_description: PentairBinarySensorEntityDescription

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if isinstance(device_data := self.get_device(), dict):
            return self.entity_description.is_on(device_data)
        return None
