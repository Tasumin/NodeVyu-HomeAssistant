"""Camera entities for NodeVyu NVR streams."""
from __future__ import annotations

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NodeVyuCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: NodeVyuCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data or {}
    location = data.get("location") or {}
    location_id = str(location.get("id") or entry.unique_id)
    async_add_entities(NodeVyuNvrCamera(coordinator, location_id, camera) for camera in data.get("cameras") or [])


class NodeVyuNvrCamera(CoordinatorEntity[NodeVyuCoordinator], Camera):
    """A camera channel exposed by a NodeVyu-managed NVR."""
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: NodeVyuCoordinator, location_id: str, camera: dict) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self.location_id = location_id
        self.camera_id = str(camera["id"])
        self.nvr_id = str(camera["nvr_id"])
        self.camera_name = str(camera.get("name") or "Camera")
        self._attr_unique_id = f"nvr_stream_{self.camera_id}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, f"nvr_stream:{self.camera_id}")}, name=self.camera_name, manufacturer="NodeVyu", model="NVR Camera", via_device=(DOMAIN, self.nvr_id))

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and any(str(camera.get("id")) == self.camera_id and bool(camera.get("stream_available")) for camera in (self.coordinator.data or {}).get("cameras") or [])

    @property
    def extra_state_attributes(self) -> dict:
        for camera in (self.coordinator.data or {}).get("cameras") or []:
            if str(camera.get("id")) == self.camera_id:
                return {"nvr_id": camera.get("nvr_id"), "channel": camera.get("channel"), "camera_identity_id": camera.get("identity_id")}
        return {}

    async def async_camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        return await self.coordinator.api.async_camera_image(self.camera_id)
