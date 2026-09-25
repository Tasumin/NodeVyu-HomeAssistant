"""Local HTTP bridge from NodeVyu fMP4 WebSocket streams to Home Assistant."""
from __future__ import annotations

import logging

from aiohttp import WSMsgType, web
from homeassistant.components.http import HomeAssistantView

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
_INIT = 0
_MEDIA = 1


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

        statuses = domain_data.setdefault("live_status", {})
        status_key = (entry_id, camera_id)
        statuses[status_key] = "starting"

        response = web.StreamResponse(
            status=200,
            headers={
                "Content-Type": "video/mp4",
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )
        await response.prepare(request)
        socket = None
        sent_init = False
        sent_media = False
        try:
            socket = await coordinator.api.async_open_live_websocket(camera_id)
            statuses[status_key] = "waiting_for_video"
            async for message in socket:
                if message.type == WSMsgType.BINARY:
                    frame = bytes(message.data)
                    if len(frame) < 2:
                        continue
                    kind = frame[0]
                    payload = frame[1:]
                    if kind == _INIT:
                        sent_init = True
                        await response.write(payload)
                    elif kind == _MEDIA and sent_init:
                        await response.write(payload)
                        if not sent_media:
                            sent_media = True
                            statuses[status_key] = "live"
                    else:
                        if kind not in (_INIT, _MEDIA):
                            _LOGGER.debug("Ignoring unknown NodeVyu live frame type %s for camera %s", kind, camera_id)
                elif message.type == WSMsgType.TEXT:
                    _LOGGER.debug("NodeVyu live control for %s: %s", camera_id, message.data)
                elif message.type in (WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR):
                    break
        except (ConnectionResetError, RuntimeError):
            statuses[status_key] = "unavailable"
        finally:
            if socket is not None and not socket.closed:
                await socket.close()
            if statuses.get(status_key) != "unavailable":
                statuses[status_key] = "idle"
            try:
                await response.write_eof()
            except (ConnectionResetError, RuntimeError):
                pass
        return response
