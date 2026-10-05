"""Poll the lamp state over the LAN."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, PROPS, SCAN_INTERVAL
from .miio import MiioClient, MiioError

_LOGGER = logging.getLogger(__name__)


class ArwenCoordinator(DataUpdateCoordinator[dict[str, str]]):
    """Read all properties with one get_prop call; the lamp sends no local push updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: MiioClient, info: dict) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.client = client
        self.info = info

    async def _async_update_data(self) -> dict[str, str]:
        try:
            values = await self.hass.async_add_executor_job(self.client.send, "get_prop", list(PROPS))
        except MiioError as err:
            raise UpdateFailed(str(err)) from err
        return dict(zip(PROPS, values))

    async def async_send(self, commands: list[tuple[str, list[Any]]]) -> None:
        """Send commands in order, then refresh the state."""
        for method, params in commands:
            _LOGGER.debug("%s %s", method, params)
            try:
                await self.hass.async_add_executor_job(self.client.send, method, params)
            except MiioError as err:
                _LOGGER.warning("Command failed: %s", err)
                break
        await self.async_request_refresh()
