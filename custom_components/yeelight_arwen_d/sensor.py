"""Diagnostic sensors from miIO.info: Wi-Fi signal, IP address and last restart."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT, EntityCategory
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
    """Add the diagnostic sensors."""
    coordinator = entry.runtime_data
    async_add_entities([SignalSensor(coordinator), IpSensor(coordinator), RestartSensor(coordinator)])


class ArwenDiagnosticSensor(ArwenEntity, SensorEntity):
    """Sensor shown under Diagnostic on the device page."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: ArwenCoordinator, key: str, name: str) -> None:
        super().__init__(coordinator, key)
        self._attr_name = name


class SignalSensor(ArwenDiagnosticSensor):
    """Wi-Fi signal strength in dBm."""

    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT

    def __init__(self, coordinator: ArwenCoordinator) -> None:
        super().__init__(coordinator, "signal", "Wi-Fi signal")

    @property
    def native_value(self) -> int | None:
        return self.coordinator.info.get("ap", {}).get("rssi")


class IpSensor(ArwenDiagnosticSensor):
    """IP address the lamp is reached at."""

    def __init__(self, coordinator: ArwenCoordinator) -> None:
        super().__init__(coordinator, "ip_address", "IP address")

    @property
    def native_value(self) -> str:
        return self.coordinator.client.host


class RestartSensor(ArwenDiagnosticSensor):
    """Time of the last restart, computed from the uptime when miIO.info is read."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: ArwenCoordinator) -> None:
        super().__init__(coordinator, "last_restart", "Last restart")

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.boot_time
