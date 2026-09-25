"""Camera entities for NodeVyu NVR streams."""
from __future__ import annotations

import secrets

from homeassistant.components.camera import Camera, CameraEntityFeature
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
    keys = hass.data[DOMAIN].setdefault("live_keys", {})
    hass.data[DOMAIN].setdefault("live_status", {})
    entities = []
    for camera in data.get("cameras") or []:
        camera_id = str(camera["id"])
        key = secrets.token_urlsafe(32)
        keys[(entry.entry_id, camera_id)] = key
        entities.append(NodeVyuNvrCamera(coordinator, location_id, camera, entry.entry_id, key))
    async_add_entities(entities)


class NodeVyuNvrCamera(CoordinatorEntity[NodeVyuCoordinator], Camera):
    """A camera channel exposed by a NodeVyu-managed NVR."""
    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = CameraEntityFeature.STREAM

    def __init__(self, coordinator: NodeVyuCoordinator, location_id: str, camera: dict, entry_id: str, live_key: str) -> None:
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self.location_id = location_id
        self.camera_id = str(camera["id"])
        self.nvr_id = str(camera["nvr_id"])
        self.camera_name = str(camera.get("name") or "Camera")
        self.entry_id = entry_id
        self.live_key = live_key
        self._attr_unique_id = f"nvr_stream_{self.camera_id}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, f"nvr_stream:{self.camera_id}")},
            name=self.camera_name,
            manufacturer="NodeVyu",
            model="NVR Camera",
        )

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and any(str(camera.get("id")) == self.camera_id and bool(camera.get("stream_available")) for camera in (self.coordinator.data or {}).get("cameras") or [])

    @property
    def extra_state_attributes(self) -> dict:
        attributes = {}
        for camera in (self.coordinator.data or {}).get("cameras") or []:
            if str(camera.get("id")) == self.camera_id:
                attributes = {"nvr_id": camera.get("nvr_id"), "channel": camera.get("channel"), "camera_identity_id": camera.get("identity_id")}
                break
        status = self.hass.data.get(DOMAIN, {}).get("live_status", {}).get((self.entry_id, self.camera_id), "idle")
        attributes["stream_status"] = status
        if status in ("starting", "waiting_for_video"):
            attributes["stream_message"] = "Starting NodeVyu live stream... Please wait."
        elif status == "live":
            attributes["stream_message"] = "Live"
        return attributes

    async def async_camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        return await self.coordinator.api.async_camera_image(self.camera_id)

    async def stream_source(self) -> str | None:
        """Return the local fMP4 bridge URL consumed by Home Assistant/FFmpeg."""
        statuses = self.hass.data[DOMAIN].setdefault("live_status", {})
        statuses[(self.entry_id, self.camera_id)] = "starting"
        self.async_write_ha_state()
        return f"http://127.0.0.1:8123/api/nodevyu/live/{self.entry_id}/{self.camera_id}/{self.live_key}"
