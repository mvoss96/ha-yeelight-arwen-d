"""Poll the lamp state over the LAN."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import CONF_DID, DOMAIN, INFO_EVERY_POLLS, PROPS, REDISCOVERY_INTERVAL, SCAN_INTERVAL
from .miio import MiioClient, MiioError, MiioTimeout, discover

_LOGGER = logging.getLogger(__name__)


class ArwenCoordinator(DataUpdateCoordinator[dict[str, str]]):
    """Read all properties with one get_prop call; the lamp sends no local push updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: MiioClient) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.client = client
        self.info: dict[str, Any] = {}
        self.boot_time: datetime | None = None
        self._last_discovery = 0.0
        self._polls = 0

    async def async_call(self, method: str, params: Any) -> Any:
        """Send one command; if the lamp does not answer, look for it under a new IP and retry once."""
        try:
            return await self.hass.async_add_executor_job(self.client.send, method, params)
        except MiioTimeout:
            if not await self._async_rediscover():
                raise
        return await self.hass.async_add_executor_job(self.client.send, method, params)

    async def async_refresh_info(self) -> None:
        """Read miIO.info (model, firmware, Wi-Fi, uptime) without keeping the token it contains."""
        info = await self.async_call("miIO.info", [])
        info.pop("token", None)
        self.info = info
        # Computed once per refresh; recomputing it on every poll would drift with the stale uptime.
        boot = dt_util.utcnow() - timedelta(seconds=info.get("life", 0))
        self.boot_time = boot.replace(second=0, microsecond=0)

    async def _async_rediscover(self) -> bool:
        """Find the lamp by its device id; return True if it answered under a different IP."""
        if time.monotonic() - self._last_discovery < REDISCOVERY_INTERVAL:
            return False
        self._last_discovery = time.monotonic()
        found = await self.hass.async_add_executor_job(discover)
        host = found.get(self.config_entry.data.get(CONF_DID))
        if host is None or host == self.client.host:
            return False
        _LOGGER.info("Lamp moved from %s to %s", self.client.host, host)
        self.client.host = host
        self.hass.config_entries.async_update_entry(
            self.config_entry, data={**self.config_entry.data, CONF_HOST: host}
        )
        return True

    async def _async_update_data(self) -> dict[str, str]:
        try:
            values = await self.async_call("get_prop", list(PROPS))
        except MiioError as err:
            raise UpdateFailed(str(err)) from err
        self._polls += 1
        if self._polls % INFO_EVERY_POLLS == 0:
            try:
                await self.async_refresh_info()
            except MiioError as err:
                _LOGGER.debug("miIO.info failed: %s", err)
        return dict(zip(PROPS, values))

    async def async_send(self, commands: list[tuple[str, list[Any]]]) -> None:
        """Send commands in order, then refresh the state; a failed command raises in the service call."""
        try:
            for method, params in commands:
                _LOGGER.debug("%s %s", method, params)
                await self.async_call(method, params)
        except MiioError as err:
            raise HomeAssistantError(f"Lamp command failed: {err}") from err
        finally:
            await self.async_request_refresh()
