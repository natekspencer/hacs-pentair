"""The Pentair integration."""

from __future__ import annotations

import asyncio

from pypentair import Pentair, PentairAuthenticationError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceEntry

from .const import CONF_ID_TOKEN, CONF_REFRESH_TOKEN, DOMAIN
from .coordinator import (
    PentairDataUpdateCoordinator,
    PentairDeviceDataUpdateCoordinator,
)

type PentairConfigEntry = ConfigEntry[PentairDataUpdateCoordinator]

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: PentairConfigEntry) -> bool:
    """Set up Pentair from a config entry."""
    entry.add_update_listener(update_listener)

    client = Pentair(
        username=entry.data.get(CONF_USERNAME),
        access_token=entry.data.get(CONF_ACCESS_TOKEN),
        id_token=entry.data.get(CONF_ID_TOKEN),
        refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
    )

    try:
        await hass.async_add_executor_job(client.get_auth)
    except PentairAuthenticationError as err:
        raise ConfigEntryAuthFailed(err) from err
    except Exception as ex:
        raise ConfigEntryNotReady(ex) from ex

    coordinator = PentairDataUpdateCoordinator(
        hass=hass, config_entry=entry, client=client
    )
    await coordinator.async_config_entry_first_refresh()

    for device in coordinator.get_devices():
        device_coordinator = PentairDeviceDataUpdateCoordinator(
            hass=hass, config_entry=entry, client=client, device_id=device["deviceId"]
        )
        coordinator.device_coordinators.append(device_coordinator)

    await asyncio.gather(
        *(
            dc.async_config_entry_first_refresh()
            for dc in coordinator.device_coordinators
        )
    )

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: PentairConfigEntry) -> bool:
    """Unload config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: PentairConfigEntry) -> None:
    """Handle removal of an entry."""
    client = Pentair(
        username=entry.data.get(CONF_USERNAME),
        access_token=entry.data.get(CONF_ACCESS_TOKEN),
        id_token=entry.data.get(CONF_ID_TOKEN),
        refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
    )
    await hass.async_add_executor_job(client.logout)


async def update_listener(hass: HomeAssistant, entry: PentairConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: PentairConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Remove a config entry from a device."""
    return not any(
        identifier
        for identifier in device_entry.identifiers
        if identifier[0] == DOMAIN
        for device in config_entry.runtime_data.get_devices()
        if identifier[1] == device["deviceId"]
    )
