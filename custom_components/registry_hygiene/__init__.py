"""Registry Hygiene: surface valid-but-badly-organised entities as Repairs."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)

from .rules import needs_area

DOMAIN = "registry_hygiene"
ISSUE_MISSING_AREA = "missing_area_entities"
MAX_LISTED = 15


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Check the registry once, now. Nothing here polls."""
    _sync_missing_area_issue(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Take the repairs down with the integration: they are its only output."""
    ir.async_delete_issue(hass, DOMAIN, ISSUE_MISSING_AREA)
    return True


def _entities_without_area(hass: HomeAssistant) -> list[str]:
    device_reg = dr.async_get(hass)
    found = []
    for entity in er.async_get(hass).entities.values():
        device = device_reg.async_get(entity.device_id) if entity.device_id else None
        device_area = device.area_id if device else None
        if needs_area(entity.area_id, device_area, entity.disabled_by):
            found.append(entity.entity_id)
    return sorted(found)


def _sync_missing_area_issue(hass: HomeAssistant) -> None:
    entities = _entities_without_area(hass)
    if not entities:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_MISSING_AREA)
        return

    listed = "\n".join(f"- `{entity_id}`" for entity_id in entities[:MAX_LISTED])
    if len(entities) > MAX_LISTED:
        listed += f"\n- … {len(entities) - MAX_LISTED} more"

    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_MISSING_AREA,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_MISSING_AREA,
        translation_placeholders={"count": str(len(entities)), "entities": listed},
    )
