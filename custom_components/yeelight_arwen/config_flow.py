"""Config flow for Yeelight Arwen."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.helpers.device_registry import format_mac

from .const import DOMAIN, SUPPORTED_MODELS
from .miio import MiioClient, MiioError


class ArwenConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up a lamp from its IP address and miIO token."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for host and token and check that the lamp answers."""
        errors: dict[str, str] = {}
        if user_input is not None:
            token = user_input[CONF_TOKEN].strip().lower()
            if not re.fullmatch(r"[0-9a-f]{32}", token):
                errors[CONF_TOKEN] = "invalid_token"
            else:
                client = MiioClient(user_input[CONF_HOST], token)
                try:
                    info = await self.hass.async_add_executor_job(client.send, "miIO.info", [])
                except MiioError:
                    errors["base"] = "cannot_connect"
                else:
                    if info["model"] not in SUPPORTED_MODELS:
                        errors["base"] = "unsupported_model"
                    else:
                        await self.async_set_unique_id(format_mac(info["mac"]))
                        self._abort_if_unique_id_configured(updates={CONF_HOST: user_input[CONF_HOST]})
                        return self.async_create_entry(
                            title="Yeelight Arwen",
                            data={CONF_HOST: user_input[CONF_HOST], CONF_TOKEN: token},
                        )

        schema = vol.Schema({vol.Required(CONF_HOST): str, vol.Required(CONF_TOKEN): str})
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )
