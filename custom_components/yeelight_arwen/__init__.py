"""Local control of Yeelight Arwen ceiling lights over miIO."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .coordinator import ArwenCoordinator
from .miio import MiioClient, MiioError

PLATFORMS = [Platform.LIGHT]

type ArwenConfigEntry = ConfigEntry[ArwenCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: ArwenConfigEntry) -> bool:
    """Connect to the lamp and start polling."""
    client = MiioClient(entry.data[CONF_HOST], entry.data[CONF_TOKEN])
    try:
        info = await hass.async_add_executor_job(client.send, "miIO.info", [])
    except MiioError as err:
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = ArwenCoordinator(hass, entry, client, info)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ArwenConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
