"""Sensors for NodeVyu."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
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
    entities: list[SensorEntity] = []
    for agent in data.get("agents") or []:
        entities.append(NodeVyuAgentVersion(coordinator, location_id, agent))
    async_add_entities(entities)


class NodeVyuAgentVersion(NodeVyuEntity, SensorEntity):
    _attr_name = "Agent version"
    _attr_icon = "mdi:package-up"

    def __init__(self, coordinator: NodeVyuCoordinator, location_id: str, agent: dict) -> None:
        self.agent_id = str(agent["id"])
        super().__init__(coordinator, location_id, self.agent_id, str(agent.get("name") or "NodeVyu agent"))
        self._attr_unique_id = f"{self.agent_id}_version"

    @property
    def native_value(self) -> str | None:
        for agent in (self.coordinator.data or {}).get("agents") or []:
            if str(agent.get("id")) == self.agent_id:
                return agent.get("agent_version")
        return None
