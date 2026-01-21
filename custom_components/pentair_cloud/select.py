"""Support for Pentair select (pump program selection)."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import PentairDataUpdateCoordinator, PentairEntity

_LOGGER = logging.getLogger(__name__)

OPTION_OFF = "Off"


@dataclass
class PentairSelectEntityDescription(SelectEntityDescription):
    """Pentair select entity description."""

    programs: dict[str, int] = field(default_factory=dict)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Pentair select using config entry."""
    coordinator: PentairDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[PentairProgramSelectEntity] = []

    # Create select entities for IF31 pumps
    for device in coordinator.get_devices("IF31"):
        device_id = device["deviceId"]
        fields = device.get("fields", {})

        # Build list of active programs (1-14)
        programs: dict[str, int] = {}
        for program_id in range(1, 15):
            # Check if program is active (zp{N}e13 == "1")
            # Fields are normalized to simple values: {"zp1e13": "1"}
            active_value = fields.get(f"zp{program_id}e13")
            if active_value != "1":
                continue

            # Get program name
            program_name = fields.get(f"zp{program_id}e2", f"Program {program_id}")
            programs[program_name] = program_id

        if not programs:
            continue

        # Build options list with "Off" as first option
        options = [OPTION_OFF] + list(programs.keys())

        description = PentairSelectEntityDescription(
            key="running_program",
            name="Running program",
            options=options,
            programs=programs,
        )

        entities.append(
            PentairProgramSelectEntity(
                coordinator=coordinator,
                config_entry=config_entry,
                description=description,
                device_id=device_id,
            )
        )

    if not entities:
        return

    async_add_entities(entities)


class PentairProgramSelectEntity(PentairEntity, SelectEntity):
    """Pentair pump program select entity."""

    entity_description: PentairSelectEntityDescription

    @property
    def current_option(self) -> str | None:
        """Return the currently selected program."""
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
            return OPTION_OFF

        if running_program >= 99:
            return OPTION_OFF

        # s14 is 0-indexed, so add 1 to get program_id
        running_id = running_program + 1

        # Find the program name for this ID
        for name, prog_id in self.entity_description.programs.items():
            if prog_id == running_id:
                return name

        return OPTION_OFF

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option == OPTION_OFF:
            # Stop the currently running program
            device = self.get_device()
            if device:
                fields = device.get("fields", {})
                # Fields are normalized to simple values: {"s14": "0"}
                running_value = fields.get("s14", "99")
                try:
                    running_program = int(running_value)
                    if running_program < 99:
                        # Stop the running program
                        await self.hass.async_add_executor_job(
                            self.coordinator.api.stop_program,
                            self._device_id,
                            running_program + 1,
                        )
                except (ValueError, TypeError):
                    pass
        else:
            # Start the selected program
            program_id = self.entity_description.programs.get(option)
            if program_id:
                await self.hass.async_add_executor_job(
                    self.coordinator.api.start_program,
                    self._device_id,
                    program_id,
                )

        await self.coordinator.async_request_refresh()
