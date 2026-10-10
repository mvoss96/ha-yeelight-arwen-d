"""Poll the lamp state over the LAN."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DID,
    DOMAIN,
    INFO_INTERVAL,
    MODEL_CEILING3,
    PROPS,
    PROPS_CEILING3,
    PUSH_SCAN_INTERVAL,
    REDISCOVERY_INTERVAL,
    SCAN_INTERVAL,
)
from .miio import MiioClient, MiioError, MiioTimeout, discover

_LOGGER = logging.getLogger(__name__)


class ArwenCoordinator(DataUpdateCoordinator[dict[str, str]]):
    """Read all properties with one get_prop call.

    The Arwen D sends no local push updates and is polled every 3 s. The ceiling3 pushes its
    changes over the Yeelight LAN protocol (lan.py); while that connection is open it is polled
    once a minute.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: MiioClient) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.client = client
        self.info: dict[str, Any] = {}
        self.boot_time: datetime | None = None
        # monotonic() starts near 0 at host boot, so 0.0 would block discovery for the first minute.
        self._last_discovery = -REDISCOVERY_INTERVAL
        self._last_info = 0.0

    @property
    def model(self) -> str:
        return self.info["model"]

    @property
    def props(self) -> tuple[str, ...]:
        return PROPS_CEILING3 if self.model == MODEL_CEILING3 else PROPS

    @callback
    def async_set_push_connected(self, connected: bool) -> None:
        """Poll rarely while the lamp pushes its state, every 3 s otherwise.

        The state is read at once, because changes before the connection opened were not pushed
        and a lost connection may mean the lamp lost power.
        """
        self.update_interval = PUSH_SCAN_INTERVAL if connected else SCAN_INTERVAL
        self._async_refresh_now()

    @callback
    def async_handle_push(self, params: dict[str, Any]) -> None:
        """Read the state after the lamp reports a change.

        The pushed values are not applied: a push arrives about 0.2 s after the change, so while
        a knob is turned quickly it can be older than the state already read after a later command.
        """
        self._async_refresh_now()

    @callback
    def _async_refresh_now(self) -> None:
        self.config_entry.async_create_background_task(self.hass, self.async_refresh(), "yeelight_arwen_d refresh")

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
        self._last_info = time.monotonic()
        # Uptime is whole seconds read with network delay, so each computation differs by about 1 s.
        # Only a difference of more than a minute is taken as a real restart.
        boot = dt_util.utcnow() - timedelta(seconds=info.get("life", 0))
        if self.boot_time is None or abs(boot - self.boot_time) > timedelta(minutes=1):
            self.boot_time = boot.replace(microsecond=0)

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
            values = await self.async_call("get_prop", list(self.props))
        except MiioError as err:
            raise UpdateFailed(str(err)) from err
        # Counted by time, not by polls: the state is also read after every command and on every push.
        if time.monotonic() - self._last_info >= INFO_INTERVAL:
            try:
                await self.async_refresh_info()
            except MiioError as err:
                _LOGGER.debug("miIO.info failed: %s", err)
        return dict(zip(self.props, values))

    async def async_send(self, commands: list[tuple[str, list[Any]]]) -> None:
        """Send commands in order, then read the state; a failed command raises in the service call.

        The state is read before the action returns, so the next step of a knob turned quickly
        sees the new value instead of the one from before the previous step. Push updates arrive
        only about 0.2 s later.
        """
        try:
            for method, params in commands:
                _LOGGER.debug("%s %s", method, params)
                await self.async_call(method, params)
        except MiioError as err:
            raise HomeAssistantError(f"Lamp command failed: {err}") from err
        finally:
            await self.async_refresh()
