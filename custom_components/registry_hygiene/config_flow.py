"""Config flow: single instance, no options yet."""

from __future__ import annotations

from homeassistant.config_entries import ConfigFlow

from . import DOMAIN


class RegistryHygieneConfigFlow(ConfigFlow, domain=DOMAIN):
    """One entry, created by clicking through a single confirmation."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Confirm, then create the single entry. There is nothing to ask."""
        if user_input is None:
            return self.async_show_form(step_id="user")
        return self.async_create_entry(title="Registry Hygiene", data={})
