"""Async client for the NodeVyu Home Assistant API."""
from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

from aiohttp import ClientError, ClientSession, ClientTimeout


class NodeVyuApiError(Exception):
    """Base NodeVyu API error."""


class NodeVyuAuthError(NodeVyuApiError):
    """NodeVyu rejected the integration token."""


class NodeVyuApi:
    def __init__(self, session: ClientSession, base_url: str, token: str) -> None:
        self._session = session
        self.base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {token}"}

    async def async_status(self) -> dict[str, Any]:
        try:
            async with self._session.get(f"{self.base_url}/api/integrations/home-assistant/status", headers=self._headers, timeout=ClientTimeout(total=15)) as response:
                if response.status in (401, 403): raise NodeVyuAuthError("Invalid or unauthorized NodeVyu token")
                if response.status >= 400: raise NodeVyuApiError(f"NodeVyu returned HTTP {response.status}")
                return await response.json()
        except NodeVyuApiError: raise
        except (ClientError, asyncio.TimeoutError, ValueError) as err: raise NodeVyuApiError(str(err)) from err

    async def async_camera_image(self, camera_id: str) -> bytes | None:
        try:
            async with self._session.get(f"{self.base_url}/api/integrations/home-assistant/cameras/{camera_id}/snapshot", headers=self._headers, timeout=ClientTimeout(total=15)) as response:
                if response.status == 404: return None
                if response.status in (401, 403): raise NodeVyuAuthError("Invalid or unauthorized NodeVyu token")
                if response.status >= 400: raise NodeVyuApiError(f"NodeVyu snapshot returned HTTP {response.status}")
                return await response.read()
        except NodeVyuApiError: raise
        except (ClientError, asyncio.TimeoutError) as err: raise NodeVyuApiError(str(err)) from err

    async def async_events(self, after: int = 0) -> AsyncIterator[dict[str, Any]]:
        headers = {**self._headers, "Accept": "text/event-stream"}
        if after: headers["Last-Event-ID"] = str(after)
        try:
            async with self._session.get(f"{self.base_url}/api/integrations/home-assistant/stream", headers=headers, timeout=ClientTimeout(total=70)) as response:
                if response.status in (401, 403): raise NodeVyuAuthError("Invalid or unauthorized NodeVyu token")
                if response.status >= 400: raise NodeVyuApiError(f"NodeVyu stream returned HTTP {response.status}")
                event_name = "message"; event_id: int | None = None; data_lines: list[str] = []
                async for raw in response.content:
                    line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                    if not line:
                        if data_lines:
                            try: payload = json.loads("\n".join(data_lines))
                            except json.JSONDecodeError: payload = {"raw": "\n".join(data_lines)}
                            yield {"event": event_name, "id": event_id, "data": payload}
                        event_name, event_id, data_lines = "message", None, []
                    elif line.startswith(":"): continue
                    elif line.startswith("event:"): event_name = line[6:].strip()
                    elif line.startswith("id:"):
                        try: event_id = int(line[3:].strip())
                        except ValueError: event_id = None
                    elif line.startswith("data:"): data_lines.append(line[5:].strip())
        except NodeVyuApiError: raise
        except (ClientError, asyncio.TimeoutError) as err: raise NodeVyuApiError(str(err)) from err
