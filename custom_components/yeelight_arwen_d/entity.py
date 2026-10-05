"""Base entity with the device info shared by all platforms."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ArwenCoordinator


class ArwenEntity(CoordinatorEntity[ArwenCoordinator]):
    """Entity of one Yeelight Arwen D lamp."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ArwenCoordinator, key: str) -> None:
        super().__init__(coordinator)
        info = coordinator.info
        unique_id = coordinator.config_entry.unique_id
        self._attr_unique_id = f"{unique_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            connections={(CONNECTION_NETWORK_MAC, info["mac"])},
            manufacturer="Yeelight",
            model=info["model"],
            name="Yeelight Arwen D",
            sw_version=info["fw_ver"],
        )
