"""The one repair that can fix itself.

Only the label rules get a button, and the reason is worth keeping: a rule
already says which labels to apply, so there is nothing left to choose. The
area repair deliberately has none -- which room a device is in is a judgment,
and a dropdown inside a repair dialog would be a worse copy of the one already
on the device page.

Where there is a device, the flow asks which of the two to label first. That is
not a courtesy: keywords match the entity id, and Home Assistant builds an
entity id out of the device's name, so a detector called "Salon capteur
mouvement" puts the word `mouvement` into `sensor.salon_capteur_mouvement_
temperature` as surely as into its occupancy entity. Fifteen repairs on one
instance were three devices. A rule counts a label on the device as carried, so
labelling there answers all of them in one press.

Both steps re-read the registry rather than trusting what the issue was raised
with, so pressing the button on a repair that has been sitting there for a week
cannot write back a stale set of labels.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    label_registry as lr,
)


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict[str, Any] | None
) -> RepairsFlow:
    """Home Assistant asks for this when the Fix button is pressed."""
    return ApplyLabelsFlow(data or {})


class ApplyLabelsFlow(RepairsFlow):
    """Add the rule's labels, to the entity or to its device."""

    def __init__(self, data: dict[str, Any]) -> None:
        """Keep what the issue was raised with; the registries are re-read."""
        self._entity_id: str = data.get("entity_id", "")
        self._labels: list[str] = list(data.get("labels", []))
        self._device_id: str | None = data.get("device_id")

    async def async_step_init(self, user_input=None) -> FlowResult:
        """Offer the choice, unless there is no device to offer."""
        if not self._device_id:
            return await self.async_step_entity()

        return self.async_show_menu(
            step_id="init",
            menu_options=["device", "entity"],
            description_placeholders=self._placeholders(),
        )

    async def async_step_device(self, user_input=None) -> FlowResult:
        """Label the device, which covers every entity hanging off it."""
        registry = dr.async_get(self.hass)
        device = registry.async_get(self._device_id) if self._device_id else None

        if device is None:
            return self.async_create_entry(data={})

        if user_input is not None:
            registry.async_update_device(
                device.id, labels=device.labels | set(self._labels)
            )
            return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema({}),
            description_placeholders=self._placeholders(),
        )

    async def async_step_entity(self, user_input=None) -> FlowResult:
        """Label just this entity."""
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

        return self.async_show_form(
            step_id="entity",
            data_schema=vol.Schema({}),
            description_placeholders=self._placeholders(),
        )

    def _placeholders(self) -> dict[str, str]:
        """Everything the three screens name, worked out once."""
        names = lr.async_get(self.hass)
        device = (
            dr.async_get(self.hass).async_get(self._device_id)
            if self._device_id
            else None
        )
        covered = (
            len(er.async_entries_for_device(er.async_get(self.hass), device.id))
            if device
            else 0
        )

        return {
            "entity_id": self._entity_id,
            "labels": ", ".join(
                found.name if (found := names.async_get_label(label)) else label
                for label in self._labels
            ),
            "device": (device.name_by_user or device.name or device.id)
            if device
            else "",
            "count": str(covered),
        }
