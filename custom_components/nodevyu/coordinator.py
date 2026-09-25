"""NodeVyu data coordinator and real-time event listener."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NodeVyuApi, NodeVyuApiError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class NodeVyuCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, api: NodeVyuApi) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api
        self.last_event_id = 0
        self._stream_task: asyncio.Task | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.api.async_status()
        except NodeVyuApiError as err:
            raise UpdateFailed(str(err)) from err

    def start_stream(self) -> None:
        """Start the long-lived event listener as a background task.

        Do not use hass.async_create_task here. Tasks created that way during
        integration setup are tracked by Home Assistant's startup machinery,
        so a deliberately long-lived SSE listener can keep HA in the startup
        phase until its timeout expires.
        """
        if self._stream_task is None or self._stream_task.done():
            self._stream_task = asyncio.create_task(
                self._stream_loop(), name="nodevyu_event_stream"
            )

    async def async_stop_stream(self) -> None:
        if self._stream_task is not None:
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass
            self._stream_task = None

    async def _stream_loop(self) -> None:
        try:
            while True:
                try:
                    async for message in self.api.async_events(self.last_event_id):
                        if message.get("id"):
                            self.last_event_id = int(message["id"])
                        event = str(message.get("event") or "")
                        payload = message.get("data") or {}
                        if event not in ("ready", "message", "error"):
                            self.hass.bus.async_fire(
                                "nodevyu_event", {"type": event, **payload}
                            )
                            # Schedule a refresh without making the persistent
                            # SSE reader wait for the HTTP status request.
                            self.async_request_refresh()
                except asyncio.CancelledError:
                    raise
                except Exception as err:  # reconnect after transient failures
                    _LOGGER.warning("NodeVyu event stream disconnected: %s", err)
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            _LOGGER.debug("NodeVyu event stream stopped")
            raise
