"""Main light and ambient light of a Yeelight Arwen D ceiling light."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ATTR_TRANSITION,
    EFFECT_OFF,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ArwenConfigEntry
from .const import (
    COLOR_MODE_CT,
    COLOR_MODE_FLOW,
    COLOR_MODE_RGB,
    EFFECT_BY_INDEX,
    EFFECT_NIGHT_LIGHT,
    EFFECTS,
    MAX_KELVIN,
    MIN_KELVIN,
    POWER_MODE_CT,
    POWER_MODE_RGB,
)
from .coordinator import ArwenCoordinator
from .entity import ArwenEntity

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ArwenConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the main light and the ambient light."""
    coordinator = entry.runtime_data
    async_add_entities([MainLight(coordinator), AmbientLight(coordinator)])


def fade(kwargs: dict[str, Any], default_ms: int) -> list[Any]:
    """Return the ["smooth", ms] / ["sudden", 0] arguments for a transition in seconds.

    Without a transition the lamp's own default (set in the Mi Home app or the
    Default transition entity) is used.
    """
    seconds = kwargs.get(ATTR_TRANSITION)
    ms = default_ms if seconds is None else int(seconds * 1000)
    # The lamp rejects smooth fades shorter than 30 ms.
    return ["smooth", ms] if ms >= 30 else ["sudden", 0]


def to_percent(brightness: int) -> int:
    return max(1, round(brightness * 100 / 255))


def num(value: str, default: int = 0) -> int:
    """Convert a get_prop value; properties a firmware does not know come back as ""."""
    return int(value) if value else default


def to_brightness(percent: str) -> int:
    return round(num(percent) * 255 / 100)


def to_rgb(value: str) -> tuple[int, int, int]:
    v = num(value)
    return (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF


def from_rgb(rgb: tuple[int, int, int]) -> int:
    return max(1, (rgb[0] << 16) | (rgb[1] << 8) | rgb[2])


def clamp_kelvin(kelvin: int) -> int:
    return min(MAX_KELVIN, max(MIN_KELVIN, kelvin))


class ArwenLight(ArwenEntity, LightEntity):
    """Common setup of both lights."""

    _attr_supported_color_modes = {ColorMode.COLOR_TEMP, ColorMode.RGB}
    _attr_min_color_temp_kelvin = MIN_KELVIN
    _attr_max_color_temp_kelvin = MAX_KELVIN

    def __init__(self, coordinator: ArwenCoordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self._update_from_data()

    @property
    def _default_ms(self) -> int:
        return num(self.coordinator.data["trans_interval_dflt"])

    def _handle_coordinator_update(self) -> None:
        self._update_from_data()
        super()._handle_coordinator_update()

    def _update_from_data(self) -> None:
        raise NotImplementedError


class MainLight(ArwenLight):
    """Main light: white, RGB, night light and the effects of the addressable LED ring."""

    _attr_name = "Primary light"
    _attr_supported_features = LightEntityFeature.TRANSITION | LightEntityFeature.EFFECT
    _attr_effect_list = [EFFECT_OFF, EFFECT_NIGHT_LIGHT, *EFFECTS]

    def __init__(self, coordinator: ArwenCoordinator) -> None:
        super().__init__(coordinator, "main")

    def _update_from_data(self) -> None:
        d = self.coordinator.data
        mode = num(d["color_mode"], COLOR_MODE_CT)
        night_light = mode != COLOR_MODE_RGB and mode != COLOR_MODE_FLOW and num(d["nl_br"]) > 0
        self._attr_is_on = d["main_power"] == "on"
        self._attr_brightness = to_brightness(d["nl_br"] if night_light else d["bright"])
        self._attr_color_temp_kelvin = clamp_kelvin(num(d["ct"], MIN_KELVIN))
        self._attr_rgb_color = to_rgb(d["rgb"])
        self._attr_color_mode = ColorMode.RGB if mode in (COLOR_MODE_RGB, COLOR_MODE_FLOW) else ColorMode.COLOR_TEMP
        if night_light:
            self._attr_effect = EFFECT_NIGHT_LIGHT
        elif mode == COLOR_MODE_FLOW:
            self._attr_effect = EFFECT_BY_INDEX.get(num(d["current_effect_index"]), EFFECT_OFF)
        else:
            self._attr_effect = EFFECT_OFF

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on and apply color, brightness or effect with the requested fade."""
        smooth = fade(kwargs, self._default_ms)
        effect = kwargs.get(ATTR_EFFECT)
        percent = to_percent(kwargs[ATTR_BRIGHTNESS]) if ATTR_BRIGHTNESS in kwargs else None
        commands: list[tuple[str, list[Any]]] = []

        # Night light has its own brightness (nl_br) and is set with one command.
        if effect == EFFECT_NIGHT_LIGHT or (
            effect is None and self._attr_effect == EFFECT_NIGHT_LIGHT and self._attr_is_on
            and ATTR_RGB_COLOR not in kwargs and ATTR_COLOR_TEMP_KELVIN not in kwargs
        ):
            moon = percent or to_percent(self._attr_brightness or 128)
            await self.coordinator.async_send([("set_scene", ["nightlight", moon, *smooth])])
            return

        if ATTR_RGB_COLOR in kwargs:
            power_mode = POWER_MODE_RGB
        elif ATTR_COLOR_TEMP_KELVIN in kwargs or effect == EFFECT_OFF:
            power_mode = POWER_MODE_CT
        else:
            power_mode = None

        if not self._attr_is_on:
            commands.append(("set_power", ["on", *smooth] + ([power_mode] if power_mode else [])))
        elif effect == EFFECT_OFF and ATTR_COLOR_TEMP_KELVIN not in kwargs:
            commands.append(("set_power", ["on", *smooth, POWER_MODE_CT]))

        if ATTR_RGB_COLOR in kwargs:
            commands.append(("set_rgb", [from_rgb(kwargs[ATTR_RGB_COLOR]), *smooth]))
        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            commands.append(("set_ct_abx", [clamp_kelvin(kwargs[ATTR_COLOR_TEMP_KELVIN]), *smooth]))
        if effect in EFFECTS:
            commands.append(("set_fx", EFFECTS[effect]))
        if percent is not None:
            commands.append(("set_bright", [percent, *smooth]))
        await self.coordinator.async_send(commands)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off with the requested fade."""
        await self.coordinator.async_send([("set_power", ["off", *fade(kwargs, self._default_ms)])])


class AmbientLight(ArwenLight):
    """RGB ambient light around the ceiling light."""

    _attr_name = "Ambient light"
    _attr_supported_features = LightEntityFeature.TRANSITION

    def __init__(self, coordinator: ArwenCoordinator) -> None:
        super().__init__(coordinator, "ambient")

    def _update_from_data(self) -> None:
        d = self.coordinator.data
        self._attr_is_on = d["bg_power"] == "on"
        self._attr_brightness = to_brightness(d["bg_bright"])
        self._attr_color_temp_kelvin = clamp_kelvin(num(d["bg_ct"], MIN_KELVIN))
        self._attr_rgb_color = to_rgb(d["bg_rgb"])
        self._attr_color_mode = ColorMode.RGB if num(d["bg_lmode"]) == COLOR_MODE_RGB else ColorMode.COLOR_TEMP

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on and apply color and brightness with the requested fade."""
        smooth = fade(kwargs, self._default_ms)
        commands: list[tuple[str, list[Any]]] = []
        if not self._attr_is_on:
            if ATTR_RGB_COLOR in kwargs:
                commands.append(("bg_set_power", ["on", *smooth, POWER_MODE_RGB]))
            elif ATTR_COLOR_TEMP_KELVIN in kwargs:
                commands.append(("bg_set_power", ["on", *smooth, POWER_MODE_CT]))
            else:
                commands.append(("bg_set_power", ["on", *smooth]))
        if ATTR_RGB_COLOR in kwargs:
            commands.append(("bg_set_rgb", [from_rgb(kwargs[ATTR_RGB_COLOR]), *smooth]))
        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            commands.append(("bg_set_ct_abx", [clamp_kelvin(kwargs[ATTR_COLOR_TEMP_KELVIN]), *smooth]))
        if ATTR_BRIGHTNESS in kwargs:
            commands.append(("bg_set_bright", [to_percent(kwargs[ATTR_BRIGHTNESS]), *smooth]))
        await self.coordinator.async_send(commands)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off with the requested fade."""
        await self.coordinator.async_send([("bg_set_power", ["off", *fade(kwargs, self._default_ms)])])
