"""NodeVyu Home Assistant integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TOKEN, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NodeVyuApi
from .const import DOMAIN, PLATFORMS
from .coordinator import NodeVyuCoordinator
from .live_view import NodeVyuLiveView


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api = NodeVyuApi(async_get_clientsession(hass), entry.data[CONF_URL], entry.data[CONF_TOKEN])
    coordinator = NodeVyuCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()
    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data[entry.entry_id] = coordinator
    domain_data.setdefault("live_keys", {})
    if not domain_data.get("live_view_registered"):
        hass.http.register_view(NodeVyuLiveView())
        domain_data["live_view_registered"] = True
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.start_stream()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: NodeVyuCoordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_stop_stream()
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
        keys = hass.data[DOMAIN].get("live_keys", {})
        for item in [item for item in keys if item[0] == entry.entry_id]:
            keys.pop(item, None)
    return unloaded
