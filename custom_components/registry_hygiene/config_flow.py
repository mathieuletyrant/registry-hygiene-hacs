"""Config flow: one instance, and a checkbox per rule behind Configure."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.helpers import selector

from .const import DOMAIN, OPTION_RULES
from .rules import ALL_RULES, DEFAULT_RULES


class RegistryHygieneConfigFlow(ConfigFlow, domain=DOMAIN):
    """One entry, created by clicking through a single confirmation."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Confirm, then create the single entry. There is nothing to ask.

        The rules are options rather than data: they are the part that changes
        after installation, and asking about them here would put a decision in
        front of somebody who has not yet seen a single finding.
        """
        if user_input is None:
            return self.async_show_form(step_id="user")
        return self.async_create_entry(title="Registry Hygiene", data={})

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """The Configure button on the integration card is this method."""
        return RegistryHygieneOptionsFlow()


class RegistryHygieneOptionsFlow(OptionsFlow):
    """Which rules run.

    Only the rules. No exclusion filters by domain or by integration, on
    purpose: the per-device Ignore button already does that job, and does it
    better -- it answers about the one device in front of you rather than about
    a category, and Home Assistant is the one remembering.
    """

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Show the checkboxes, or store what came back from them."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(OPTION_RULES, list(DEFAULT_RULES))

        # A multi-select in LIST mode is what renders as a column of
        # checkboxes; the translation_key is what gives each one a sentence
        # instead of its rule id.
        checkboxes = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=list(ALL_RULES),
                multiple=True,
                mode=selector.SelectSelectorMode.LIST,
                translation_key=OPTION_RULES,
            )
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {vol.Required(OPTION_RULES, default=list(current)): checkboxes}
            ),
        )
