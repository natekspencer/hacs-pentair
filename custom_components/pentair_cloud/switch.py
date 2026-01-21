"""Support for Pentair switches (pump control)."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import PentairDataUpdateCoordinator, PentairEntity

_LOGGER = logging.getLogger(__name__)


@dataclass
class PentairProgramSwitchEntityDescription(SwitchEntityDescription):
    """Pentair program switch entity description."""

    program_id: int = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Pentair switches using config entry."""
    coordinator: PentairDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[SwitchEntity] = []

    # Create switch entities for IF31 pumps
    for device in coordinator.get_devices("IF31"):
        device_id = device["deviceId"]
        fields = device.get("fields", {})

        # Add pump enable switch
        entities.append(
            PentairPumpEnableSwitchEntity(
                coordinator=coordinator,
                config_entry=config_entry,
                description=SwitchEntityDescription(
                    key="pump_enabled",
                    name="Pump enabled",
                    icon="mdi:pump",
                ),
                device_id=device_id,
            )
        )

        # Add program switches for active programs (1-14)
        for program_id in range(1, 15):
            # Check if program is active (zp{N}e13 == "1")
            # Fields are normalized to simple values: {"zp1e13": "1"}
            active_value = fields.get(f"zp{program_id}e13")
            if active_value != "1":
                continue

            # Get program name
            program_name = fields.get(f"zp{program_id}e2", f"Program {program_id}")

            description = PentairProgramSwitchEntityDescription(
                key=f"program_{program_id}",
                name=program_name,
                program_id=program_id,
            )

            entities.append(
                PentairProgramSwitchEntity(
                    coordinator=coordinator,
                    config_entry=config_entry,
                    description=description,
                    device_id=device_id,
                )
            )

    if not entities:
        return

    async_add_entities(entities)


class PentairPumpEnableSwitchEntity(PentairEntity, SwitchEntity):
    """Pentair pump enable switch entity."""

    _optimistic_state: bool | None = None

    @property
    def is_on(self) -> bool | None:
        """Return true if the pump is enabled."""
        # Use optimistic state if set (command was just sent)
        if self._optimistic_state is not None:
            return self._optimistic_state

        device = self.get_device()
        if device is None:
            return None

        fields = device.get("fields", {})
        # d25 contains pump enabled status (1 = enabled)
        # Fields are normalized to simple values: {"d25": "1"}
        enabled_value = fields.get("d25")
        if enabled_value is None:
            return None
        return enabled_value == "1"

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Clear optimistic state when we get real data
        self._optimistic_state = None
        super()._handle_coordinator_update()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the pump."""
        self._optimistic_state = True
        self.async_write_ha_state()

        await self.hass.async_add_executor_job(
            self.coordinator.api.set_pump_enabled,
            self._device_id,
            True,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the pump."""
        self._optimistic_state = False
        self.async_write_ha_state()

        await self.hass.async_add_executor_job(
            self.coordinator.api.set_pump_enabled,
            self._device_id,
            False,
        )


class PentairProgramSwitchEntity(PentairEntity, SwitchEntity):
    """Pentair pump program switch entity."""

    entity_description: PentairProgramSwitchEntityDescription
    _optimistic_state: bool | None = None

    @property
    def is_on(self) -> bool | None:
        """Return true if the program is running."""
        # Use optimistic state if set (command was just sent)
        if self._optimistic_state is not None:
            return self._optimistic_state

        device = self.get_device()
        if device is None:
            return None

        fields = device.get("fields", {})
        # s14 contains the currently running program (0-indexed, 99 = none)
        # Fields are normalized to simple values: {"s14": "0"}
        running_value = fields.get("s14", "99")
        try:
            running_program = int(running_value)
        except (ValueError, TypeError):
            return None

        # s14 is 0-indexed, so program 1 = s14 value 0
        return running_program + 1 == self.entity_description.program_id

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Clear optimistic state when we get real data
        self._optimistic_state = None
        super()._handle_coordinator_update()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the program (start it)."""
        # Set optimistic state immediately for responsive UI
        self._optimistic_state = True
        self.async_write_ha_state()

        await self.hass.async_add_executor_job(
            self.coordinator.api.start_program,
            self._device_id,
            self.entity_description.program_id,
        )
        # Don't refresh immediately - pump needs time to update cloud state
        # The 30-second coordinator interval will pick up the confirmed state

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the program (stop it)."""
        # Set optimistic state immediately for responsive UI
        self._optimistic_state = False
        self.async_write_ha_state()

        await self.hass.async_add_executor_job(
            self.coordinator.api.stop_program,
            self._device_id,
            self.entity_description.program_id,
        )
        # Don't refresh immediately - pump needs time to update cloud state
