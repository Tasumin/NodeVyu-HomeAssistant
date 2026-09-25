"""Shared NodeVyu entity helpers."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NodeVyuCoordinator


class NodeVyuEntity(CoordinatorEntity[NodeVyuCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: NodeVyuCoordinator, location_id: str, object_id: str, name: str) -> None:
        super().__init__(coordinator)
        self.location_id = location_id
        self.object_id = object_id
        self.object_name = name

    @property
    def device_info(self) -> DeviceInfo:
        # Current Home Assistant versions no longer accept the legacy
        # via_device tuple here. Keep the NodeVyu device registration stable;
        # parent/location relationships can be added through the device
        # registry's current API later without breaking entity setup.
        return DeviceInfo(
            identifiers={(DOMAIN, self.object_id)},
            name=self.object_name,
            manufacturer="NodeVyu",
        )
