"""Main light and ambient light of a Yeelight Arwen D ceiling light."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

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
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform
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
    MODEL_CEILING3,
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
    """Add the lights of the lamp model, and the adjust action."""
    coordinator = entry.runtime_data
    if coordinator.model == MODEL_CEILING3:
        async_add_entities([Ceiling3Light(coordinator)])
    else:
        async_add_entities([MainLight(coordinator), AmbientLight(coordinator)])
    entity_platform.async_get_current_platform().async_register_entity_service(
        "adjust",
        {
            vol.Optional("brightness_step"): vol.All(vol.Coerce(int), vol.Range(-100, 100)),
            vol.Optional("color_temp_step"): vol.All(vol.Coerce(int), vol.Range(-100, 100)),
            vol.Optional(ATTR_TRANSITION): vol.All(vol.Coerce(float), vol.Range(0, 60)),
        },
        "async_adjust",
    )


def fade(kwargs: dict[str, Any], default_ms: int) -> list[Any]:
    """Return the ["smooth", ms] / ["sudden", 0] arguments for a transition in seconds.

    Without a transition the lamp's own default (set in the Mi Home app or the
    Default transition entity) is used.
    """
    seconds = kwargs.get(ATTR_TRANSITION)
    ms = default_ms if seconds is None else int(seconds * 1000)
    return ["smooth", ms] if ms > 0 else ["sudden", 0]


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


def color_power_mode(kwargs: dict[str, Any]) -> int | None:
    """Return the set_power mode that matches a requested color, or None without one."""
    if ATTR_RGB_COLOR in kwargs:
        return POWER_MODE_RGB
    if ATTR_COLOR_TEMP_KELVIN in kwargs:
        return POWER_MODE_CT
    return None


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

    @callback
    def _handle_coordinator_update(self) -> None:
        self._update_from_data()
        super()._handle_coordinator_update()

    def _update_from_data(self) -> None:
        raise NotImplementedError

    # Command prefix: "" for the primary light, "bg_" for the ambient light.
    _prefix = ""

    async def async_adjust(
        self,
        brightness_step: int | None = None,
        color_temp_step: int | None = None,
        transition: float | None = None,
    ) -> None:
        """Change brightness and/or color temperature by a percentage, computed by the lamp."""
        # adjust_* take a plain duration in ms instead of "smooth"/"sudden"; 0 changes at once.
        ms = self._default_ms if transition is None else int(transition * 1000)
        commands: list[tuple[str, list[Any]]] = []
        if brightness_step:
            commands.append((f"{self._prefix}adjust_bright", [brightness_step, ms]))
        if color_temp_step:
            commands.append((f"{self._prefix}adjust_ct", [color_temp_step, ms]))
        await self.coordinator.async_send(commands)


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

        power_mode = color_power_mode(kwargs)
        if power_mode is None and effect == EFFECT_OFF:
            power_mode = POWER_MODE_CT

        if not self._attr_is_on:
            commands.append(("set_power", ["on", *smooth] + ([power_mode] if power_mode else [])))
        elif effect == EFFECT_OFF and color_power_mode(kwargs) is None:
            # set_rgb / set_ct_abx leave the effect on their own; only a bare "off" needs set_power.
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


class Ceiling3Light(MainLight):
    """White light of a Yeelight Ceiling3 with its night light; no RGB, effects or ambient light.

    Night light uses the same commands as on the Arwen D: set_scene "nightlight" turns it on,
    set_bright and adjust_bright change its brightness, set_power mode 1 returns to white.
    """

    _attr_supported_color_modes = {ColorMode.COLOR_TEMP}
    _attr_color_mode = ColorMode.COLOR_TEMP
    _attr_effect_list = [EFFECT_OFF, EFFECT_NIGHT_LIGHT]

    def _update_from_data(self) -> None:
        d = self.coordinator.data
        night_light = d["active_mode"] == "1"
        self._attr_is_on = d["power"] == "on"
        self._attr_brightness = to_brightness(d["nl_br"] if night_light else d["bright"])
        self._attr_color_temp_kelvin = clamp_kelvin(num(d["ct"], MIN_KELVIN))
        self._attr_effect = EFFECT_NIGHT_LIGHT if night_light else EFFECT_OFF


class AmbientLight(ArwenLight):
    """RGB ambient light around the ceiling light."""

    _attr_name = "Ambient light"
    _prefix = "bg_"
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
            power_mode = color_power_mode(kwargs)
            commands.append(("bg_set_power", ["on", *smooth] + ([power_mode] if power_mode else [])))
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
