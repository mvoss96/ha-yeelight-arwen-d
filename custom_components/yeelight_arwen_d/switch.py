"""On/off settings of the Mi Home app as configuration switches."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ArwenConfigEntry
from .const import SWITCH_SETTINGS
from .coordinator import ArwenCoordinator
from .entity import ArwenEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ArwenConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add one switch per setting."""
    coordinator = entry.runtime_data
    async_add_entities([*(SettingSwitch(coordinator, key) for key in SWITCH_SETTINGS), FadeInSwitch(coordinator)])


class SettingSwitch(ArwenEntity, SwitchEntity):
    """Setting read with get_prop and written with set_ps "0"/"1"."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: ArwenCoordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self._prop, self._setting, self._attr_name = SWITCH_SETTINGS[key]

    @property
    def is_on(self) -> bool | None:
        value = self.coordinator.data[self._prop]
        # Firmware without this setting returns "": unknown, not off.
        return value == "1" if value else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_send([("set_ps", [self._setting, "1"])])

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_send([("set_ps", [self._setting, "0"])])


class FadeInSwitch(ArwenEntity, SwitchEntity):
    """Fade in when the lamp is turned on (power_on_effect), written together with the default transition."""

    _attr_name = "Fade in when turned on"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: ArwenCoordinator) -> None:
        super().__init__(coordinator, "fade_in")

    @property
    def is_on(self) -> bool | None:
        # 0 turns on at once, 1-5 fade in.
        value = self.coordinator.data["power_on_effect"]
        return value != "0" if value else None

    async def _async_set(self, effect: str) -> None:
        # set_ps trans_default takes "<default transition ms>,<power_on_effect>".
        ms = self.coordinator.data["trans_interval_dflt"]
        await self.coordinator.async_send([("set_ps", ["trans_default", f"{ms},{effect}"])])

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set("1")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set("0")
