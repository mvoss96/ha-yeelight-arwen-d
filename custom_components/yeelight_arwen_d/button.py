"""Buttons for toggling and relative changes the lamp computes itself, like the remote's keys."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ArwenConfigEntry
from .coordinator import ArwenCoordinator
from .entity import ArwenEntity
from .light import num

# key -> (entity name, miIO method, params).
# Brightness moves by 10 points; below 1 % the lamp turns off. set_adjust for brightness jumps
# in large fixed steps (50 -> 100 -> 40), so it is only used for color temperature, where it
# steps through 2700/4000/5200/6500 K.
BUTTONS: dict[str, tuple[str, str, list[Any]]] = {
    "toggle": ("Toggle", "toggle", []),
    "brightness_up": ("Brightness up", "adjust_bright", [10]),
    "brightness_down": ("Brightness down", "adjust_bright", [-10]),
    "color_temp_up": ("Color temperature up", "set_adjust", ["increase", "ct"]),
    "color_temp_down": ("Color temperature down", "set_adjust", ["decrease", "ct"]),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ArwenConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add one button per relative command of the primary light."""
    coordinator = entry.runtime_data
    async_add_entities(ArwenButton(coordinator, key) for key in BUTTONS)


class ArwenButton(ArwenEntity, ButtonEntity):
    """Send one fixed command to the primary light."""

    def __init__(self, coordinator: ArwenCoordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self._attr_name, self._method, self._params = BUTTONS[key]

    async def async_press(self) -> None:
        params = self._params
        if self._method == "adjust_bright":
            # adjust_bright needs a duration; use the lamp's default transition.
            params = [*params, num(self.coordinator.data["trans_interval_dflt"])]
        await self.coordinator.async_send([(self._method, params)])
