"""Local control of Yeelight Arwen D and Ceiling3 ceiling lights over miIO."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from . import lan
from .const import CONF_DID, MODEL_CEILING3
from .coordinator import ArwenCoordinator
from .miio import MiioClient, MiioError

PLATFORMS = [Platform.BUTTON, Platform.LIGHT, Platform.NUMBER, Platform.SENSOR, Platform.SWITCH]
# The ceiling3 has none of the Mi Home settings that the number and switch entities write.
PLATFORMS_CEILING3 = [Platform.BUTTON, Platform.LIGHT, Platform.SENSOR]

type ArwenConfigEntry = ConfigEntry[ArwenCoordinator]


def _platforms(coordinator: ArwenCoordinator) -> list[Platform]:
    return PLATFORMS_CEILING3 if coordinator.model == MODEL_CEILING3 else PLATFORMS


async def async_setup_entry(hass: HomeAssistant, entry: ArwenConfigEntry) -> bool:
    """Connect to the lamp and start polling; for the ceiling3 also listen for pushed state changes."""
    coordinator = ArwenCoordinator(hass, entry, MiioClient(entry.data[CONF_HOST], entry.data[CONF_TOKEN]))
    try:
        await coordinator.async_refresh_info()
    except MiioError as err:
        raise ConfigEntryNotReady(str(err)) from err
    if entry.data.get(CONF_DID) != coordinator.client.did:
        hass.config_entries.async_update_entry(entry, data={**entry.data, CONF_DID: coordinator.client.did})

    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    if coordinator.model == MODEL_CEILING3:
        # Cancelled automatically when the entry is unloaded.
        entry.async_create_background_task(
            hass,
            lan.listen(
                lambda: coordinator.client.host,
                coordinator.async_handle_push,
                coordinator.async_set_push_connected,
            ),
            "yeelight_arwen_d LAN push",
        )
    await hass.config_entries.async_forward_entry_setups(entry, _platforms(coordinator))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ArwenConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _platforms(entry.runtime_data))
