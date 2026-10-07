"""Default transition of the lamp as a configuration number."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ArwenConfigEntry
from .coordinator import ArwenCoordinator
from .entity import ArwenEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ArwenConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the default transition."""
    async_add_entities([DefaultTransition(entry.runtime_data)])


class DefaultTransition(ArwenEntity, NumberEntity):
    """Fade the lamp uses when a command carries no transition (Mi Home app: dimming time)."""

    _attr_name = "Default transition"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = UnitOfTime.MILLISECONDS
    # 0 changes at once; 10 s is the longest value tested.
    _attr_native_min_value = 0
    _attr_native_max_value = 10000
    _attr_native_step = 10

    def __init__(self, coordinator: ArwenCoordinator) -> None:
        super().__init__(coordinator, "default_transition")

    @property
    def native_value(self) -> int | None:
        value = self.coordinator.data["trans_interval_dflt"]
        return int(value) if value else None

    async def async_set_native_value(self, value: float) -> None:
        # trans_default also sets power_on_effect, so the current value is written back unchanged.
        effect = self.coordinator.data["power_on_effect"] or "1"
        await self.coordinator.async_send([("set_ps", ["trans_default", f"{int(value)},{effect}"])])
