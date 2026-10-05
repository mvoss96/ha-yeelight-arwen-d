"""Local control of Yeelight Arwen ceiling lights over miIO."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_DID
from .coordinator import ArwenCoordinator
from .miio import MiioClient, MiioError

PLATFORMS = [Platform.LIGHT]

type ArwenConfigEntry = ConfigEntry[ArwenCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: ArwenConfigEntry) -> bool:
    """Connect to the lamp and start polling."""
    coordinator = ArwenCoordinator(hass, entry, MiioClient(entry.data[CONF_HOST], entry.data[CONF_TOKEN]))
    try:
        coordinator.info = await coordinator.async_call("miIO.info", [])
    except MiioError as err:
        raise ConfigEntryNotReady(str(err)) from err
    if entry.data.get(CONF_DID) != coordinator.client.did:
        hass.config_entries.async_update_entry(entry, data={**entry.data, CONF_DID: coordinator.client.did})

    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ArwenConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
