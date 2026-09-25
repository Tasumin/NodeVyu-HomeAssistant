"""Local HTTP bridge from NodeVyu fMP4 WebSocket streams to Home Assistant."""
from __future__ import annotations

from aiohttp import WSMsgType, web
from homeassistant.components.http import HomeAssistantView

from .const import DOMAIN


class NodeVyuLiveView(HomeAssistantView):
    """Serve a NodeVyu live fMP4 stream to Home Assistant's stream worker."""

    url = "/api/nodevyu/live/{entry_id}/{camera_id}/{key}"
    name = "api:nodevyu:live"
    requires_auth = False

    async def get(self, request: web.Request, entry_id: str, camera_id: str, key: str) -> web.StreamResponse:
        hass = request.app["hass"]
        domain_data = hass.data.get(DOMAIN, {})
        keys = domain_data.get("live_keys", {})
        if keys.get((entry_id, camera_id)) != key:
            raise web.HTTPUnauthorized()
        coordinator = domain_data.get(entry_id)
        if coordinator is None:
            raise web.HTTPNotFound()

        response = web.StreamResponse(status=200, headers={"Content-Type": "video/mp4", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
        await response.prepare(request)
        socket = None
        try:
            socket = await coordinator.api.async_open_live_websocket(camera_id)
            async for message in socket:
                if message.type == WSMsgType.BINARY:
                    await response.write(message.data)
                elif message.type in (WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR):
                    break
        except (ConnectionResetError, RuntimeError):
            pass
        finally:
            if socket is not None and not socket.closed:
                await socket.close()
            try:
                await response.write_eof()
            except (ConnectionResetError, RuntimeError):
                pass
        return response
