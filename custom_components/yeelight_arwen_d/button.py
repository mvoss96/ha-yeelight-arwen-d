"""Buttons for relative changes the lamp computes itself, like the remote's keys."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ArwenConfigEntry
from .coordinator import ArwenCoordinator
from .entity import ArwenEntity

# key -> (entity name, miIO method, params). Step sizes are set by the lamp.
BUTTONS: dict[str, tuple[str, str, list[Any]]] = {
    "toggle": ("Toggle", "toggle", []),
    "brightness_up": ("Brightness up", "set_adjust", ["increase", "bright"]),
    "brightness_down": ("Brightness down", "set_adjust", ["decrease", "bright"]),
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
        await self.coordinator.async_send([(self._method, self._params)])
