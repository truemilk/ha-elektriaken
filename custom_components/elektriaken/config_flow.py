"""Config and options flows for Elektriaken."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_DURATION,
    CONF_RESOLUTION,
    CONF_VAT_RATE,
    DEFAULT_DURATION,
    DEFAULT_RESOLUTION,
    DEFAULT_VAT_RATE,
    DOMAIN,
    NAME,
)


def _schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_VAT_RATE, default=defaults.get(CONF_VAT_RATE, DEFAULT_VAT_RATE)
            ): NumberSelector(
                NumberSelectorConfig(min=0, max=100, step=0.1, mode=NumberSelectorMode.BOX)
            ),
            vol.Required(
                CONF_RESOLUTION, default=str(defaults.get(CONF_RESOLUTION, DEFAULT_RESOLUTION))
            ): SelectSelector(
                SelectSelectorConfig(options=["15", "60"], mode=SelectSelectorMode.DROPDOWN)
            ),
            vol.Required(
                CONF_DURATION, default=defaults.get(CONF_DURATION, DEFAULT_DURATION)
            ): NumberSelector(
                NumberSelectorConfig(
                    min=15,
                    max=1440,
                    step=15,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="min",
                )
            ),
        }
    )


class ElektriakenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle Elektriaken configuration."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Create the sole Estonia entry."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if user_input is not None:
            user_input[CONF_RESOLUTION] = int(user_input[CONF_RESOLUTION])
            user_input[CONF_DURATION] = int(user_input[CONF_DURATION])
            user_input[CONF_VAT_RATE] = float(user_input[CONF_VAT_RATE])
            if int(user_input[CONF_DURATION]) % user_input[CONF_RESOLUTION] == 0:
                return self.async_create_entry(title=NAME, data={}, options=user_input)
            return self.async_show_form(
                step_id="user", data_schema=_schema(user_input), errors={"base": "invalid_duration"}
            )
        return self.async_show_form(step_id="user", data_schema=_schema({}), errors={})

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return ElektriakenOptionsFlow()


class ElektriakenOptionsFlow(config_entries.OptionsFlow):
    """Update Elektriaken preferences."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            user_input[CONF_RESOLUTION] = int(user_input[CONF_RESOLUTION])
            user_input[CONF_DURATION] = int(user_input[CONF_DURATION])
            user_input[CONF_VAT_RATE] = float(user_input[CONF_VAT_RATE])
            if int(user_input[CONF_DURATION]) % user_input[CONF_RESOLUTION] == 0:
                return self.async_create_entry(title="", data=user_input)
            return self.async_show_form(
                step_id="init",
                data_schema=_schema(user_input),
                errors={"base": "invalid_duration"},
            )
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(dict(self.config_entry.options)),
            errors={},
        )
