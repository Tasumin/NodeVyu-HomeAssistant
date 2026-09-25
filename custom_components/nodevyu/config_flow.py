"""Config flow for NodeVyu."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_TOKEN, CONF_URL
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NodeVyuApi, NodeVyuApiError, NodeVyuAuthError
from .const import DOMAIN


class NodeVyuConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            url = str(user_input[CONF_URL]).strip().rstrip("/")
            token = str(user_input[CONF_TOKEN]).strip()
            try:
                status = await NodeVyuApi(async_get_clientsession(self.hass), url, token).async_status()
            except NodeVyuAuthError:
                errors["base"] = "invalid_auth"
            except NodeVyuApiError:
                errors["base"] = "cannot_connect"
            else:
                location = status.get("location") or {}
                location_id = str(location.get("id") or "")
                if not location_id:
                    errors["base"] = "invalid_response"
                else:
                    await self.async_set_unique_id(location_id)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=str(location.get("name") or "NodeVyu"),
                        data={CONF_URL: url, CONF_TOKEN: token},
                    )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_URL, default="https://nodevyu.com"): str,
                    vol.Required(CONF_TOKEN): str,
                }
            ),
            errors=errors,
        )
