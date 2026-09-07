"""The one repair that can fix itself.

Only the label rules get a button, and the reason is worth keeping: a rule
already says which labels to apply, so there is nothing left to choose. The
area repair deliberately has none -- which room a device is in is a judgment,
and a dropdown inside a repair dialog would be a worse copy of the one already
on the device page.

The flow re-reads the entity rather than trusting what the issue was raised
with, so pressing the button on a repair that has been sitting there for a week
cannot write back a stale set of labels.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import entity_registry as er, label_registry as lr


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict[str, Any] | None
) -> RepairsFlow:
    """Home Assistant asks for this when the Fix button is pressed."""
    return ApplyLabelsFlow(data or {})


class ApplyLabelsFlow(RepairsFlow):
    """Add the rule's labels to the entity, on one confirmation."""

    def __init__(self, data: dict[str, Any]) -> None:
        """Keep what the issue was raised with; the entity is re-read later."""
        self._entity_id: str = data.get("entity_id", "")
        self._labels: list[str] = list(data.get("labels", []))

    async def async_step_init(self, user_input=None) -> FlowResult:
        """Home Assistant enters here; there is only the one step."""
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input=None) -> FlowResult:
        """Name the labels, then add them."""
        registry = er.async_get(self.hass)
        entity = registry.async_get(self._entity_id)

        if entity is None:
            # Deleted since the repair was raised. Nothing to do, and nothing
            # worth complaining about -- the next sync drops the issue anyway.
            return self.async_create_entry(data={})

        if user_input is not None:
            registry.async_update_entity(
                self._entity_id, labels=entity.labels | set(self._labels)
            )
            return self.async_create_entry(data={})

        names = lr.async_get(self.hass)

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "entity_id": self._entity_id,
                "labels": ", ".join(
                    found.name if (found := names.async_get_label(label)) else label
                    for label in self._labels
                ),
            },
        )
