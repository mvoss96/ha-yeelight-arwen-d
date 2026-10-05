"""Config flow for Yeelight Arwen D."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .const import CONF_DID, DOMAIN, SUPPORTED_MODELS
from .miio import MiioClient, MiioError, discover


class ArwenConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up a lamp found on the network (or entered by IP) with its miIO token."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Offer the miIO devices that answer a broadcast and ask for the token."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            token = user_input[CONF_TOKEN].strip().lower()
            if not re.fullmatch(r"[0-9a-f]{32}", token):
                errors[CONF_TOKEN] = "invalid_token"
            else:
                client = MiioClient(host, token)
                try:
                    info = await self.hass.async_add_executor_job(client.send, "miIO.info", [])
                except MiioError:
                    errors["base"] = "cannot_connect"
                else:
                    if info["model"] not in SUPPORTED_MODELS:
                        errors["base"] = "unsupported_model"
                    else:
                        await self.async_set_unique_id(format_mac(info["mac"]))
                        self._abort_if_unique_id_configured(updates={CONF_HOST: host, CONF_DID: client.did})
                        return self.async_create_entry(
                            title="Yeelight Arwen D",
                            data={CONF_HOST: host, CONF_TOKEN: token, CONF_DID: client.did},
                        )

        found = await self.hass.async_add_executor_job(discover)
        configured = {entry.data.get(CONF_DID) for entry in self._async_current_entries()}
        options = [
            {"value": ip, "label": f"{ip} (ID {did})"}
            for did, ip in sorted(found.items())
            if did not in configured
        ]
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): SelectSelector(
                    SelectSelectorConfig(options=options, custom_value=True)
                ),
                vol.Required(CONF_TOKEN): str,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )
