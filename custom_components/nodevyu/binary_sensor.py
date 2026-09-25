"""Binary sensors for NodeVyu availability."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import NodeVyuCoordinator
from .entity import NodeVyuEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: NodeVyuCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data or {}
    location = data.get("location") or {}
    location_id = str(location.get("id") or entry.unique_id)
    entities: list[BinarySensorEntity] = []
    for device in data.get("devices") or []:
        entities.append(NodeVyuDeviceAvailability(coordinator, location_id, device))
    for agent in data.get("agents") or []:
        entities.append(NodeVyuAgentAvailability(coordinator, location_id, agent))
    async_add_entities(entities)


class NodeVyuDeviceAvailability(NodeVyuEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_name = "Connectivity"

    def __init__(self, coordinator: NodeVyuCoordinator, location_id: str, device: dict) -> None:
        self.device_id = str(device["id"])
        super().__init__(coordinator, location_id, self.device_id, str(device.get("name") or "NodeVyu device"))
        self._attr_unique_id = f"{self.device_id}_connectivity"

    @property
    def is_on(self) -> bool | None:
        for device in (self.coordinator.data or {}).get("devices") or []:
            if str(device.get("id")) == self.device_id:
                status = str(device.get("status") or device.get("state") or "").lower()
                if status:
                    return status in ("up", "online", "ok")
        return None


class NodeVyuAgentAvailability(NodeVyuEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_name = "Connectivity"

    def __init__(self, coordinator: NodeVyuCoordinator, location_id: str, agent: dict) -> None:
        self.agent_id = str(agent["id"])
        super().__init__(coordinator, location_id, self.agent_id, str(agent.get("name") or "NodeVyu agent"))
        self._attr_unique_id = f"{self.agent_id}_connectivity"

    @property
    def is_on(self) -> bool | None:
        for agent in (self.coordinator.data or {}).get("agents") or []:
            if str(agent.get("id")) == self.agent_id:
                return str(agent.get("status") or "").lower() == "online"
        return None
