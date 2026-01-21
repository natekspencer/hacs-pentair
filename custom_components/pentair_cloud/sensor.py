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
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfMass,
    UnitOfPower,
    UnitOfPressure,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.dt import as_local

from .const import DOMAIN
from .entity import PentairDataUpdateCoordinator, PentairEntity
from .helpers import convert_timestamp, get_field_value


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
            value_fn=lambda data: convert_timestamp(data.get("lastReport")) if data and data.get("lastReport") else None,
        ),
    ),
    "IF31": (
        PentairSensorEntityDescription(
            key="device_time",
            device_class=SensorDeviceClass.TIMESTAMP,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            translation_key="device_time",
            value_fn=lambda data: as_local(get_field_value("s1", data)),
        ),
        PentairSensorEntityDescription(
            key="estimated_flow",
            device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
            native_unit_of_measurement=UnitOfVolumeFlowRate.GALLONS_PER_MINUTE,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda data: get_field_value("s26", data),
        ),
        PentairSensorEntityDescription(
            key="motor_speed",
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            translation_key="motor_speed",
            value_fn=lambda data: get_field_value("s19", data),
        ),
        PentairSensorEntityDescription(
            key="power",
            device_class=SensorDeviceClass.POWER,
            native_unit_of_measurement=UnitOfPower.WATT,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda data: get_field_value("s18", data),
        ),
        PentairSensorEntityDescription(
            key="pressure",
            device_class=SensorDeviceClass.PRESSURE,
            native_unit_of_measurement=UnitOfPressure.PSI,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda data: get_field_value("s17", data),
        ),
        PentairSensorEntityDescription(
            key="rssi",
            device_class=SensorDeviceClass.SIGNAL_STRENGTH,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda data: get_field_value("s13", data),
        ),
    ),
    "PPA0": (
        PentairSensorEntityDescription(
            key="battery_level",
            device_class=SensorDeviceClass.BATTERY,
            entity_category=EntityCategory.DIAGNOSTIC,
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=1,
            translation_key="battery_level",
            value_fn=lambda data: min(int(get_field_value("bvl", data)) * 100 / 8, 100),
        ),
    ),
    "SSS1": (
        PentairSensorEntityDescription(
            key="average_salt_usage_per_day",
            device_class=SensorDeviceClass.WEIGHT,
            native_unit_of_measurement=UnitOfMass.POUNDS,
            state_class=SensorStateClass.MEASUREMENT,
            translation_key="average_salt_usage_per_day",
            value_fn=lambda data: get_field_value("average_salt_usage_per_day", data),
        ),
        PentairSensorEntityDescription(
            key="battery_level",
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:battery",
            state_class=SensorStateClass.MEASUREMENT,
            translation_key="battery_level",
            value_fn=lambda data: get_field_value("battery_level", data),
        ),
        PentairSensorEntityDescription(
            key="salt_level",
            state_class=SensorStateClass.MEASUREMENT,
            translation_key="salt_level",
            value_fn=lambda data: get_field_value("salt_level", data),
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
