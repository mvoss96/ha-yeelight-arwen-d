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
    # The lamp rejects smooth fades shorter than 30 ms; 10 s is the longest value tested.
    _attr_native_min_value = 30
    _attr_native_max_value = 10000
    _attr_native_step = 10

    def __init__(self, coordinator: ArwenCoordinator) -> None:
        super().__init__(coordinator, "default_transition")

    @property
    def native_value(self) -> int:
        return int(self.coordinator.data["trans_interval_dflt"] or 0)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_send([("set_ps", ["trans_default", f"{int(value)},1"])])
