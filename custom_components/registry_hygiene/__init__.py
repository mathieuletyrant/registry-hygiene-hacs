"""Registry Hygiene: surface valid-but-badly-filed devices as Repairs."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, issue_registry as ir
from homeassistant.helpers.debounce import Debouncer

from .rules import needs_area

_LOGGER = logging.getLogger(__name__)

DOMAIN = "registry_hygiene"
ISSUE_DEVICES_WITHOUT_AREA = "devices_without_area"

# The device registry churns while integrations set up: a restart fires a burst
# of events over a few seconds. The check is cheap but not free a hundred times
# over, and without a cooldown the repair would flicker its way to the right
# answer in front of whoever happens to be on the Repairs page.
DEBOUNCE_SECONDS = 5


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Check now, then again whenever the device registry moves.

    Checking only at setup was the first shape, and it is the one thing an
    integration like this cannot do: the first thing anyone does is assign the
    area and look again, and the repair would still be sitting there until the
    next restart.
    """

    async def _check(_event=None) -> None:
        _sync_issue(hass)

    debouncer = Debouncer(
        hass,
        _LOGGER,
        cooldown=DEBOUNCE_SECONDS,
        immediate=False,
        function=_check,
    )

    async def _on_device_registry_update(_event) -> None:
        await debouncer.async_call()

    entry.async_on_unload(debouncer.async_shutdown)
    entry.async_on_unload(
        hass.bus.async_listen(
            dr.EVENT_DEVICE_REGISTRY_UPDATED, _on_device_registry_update
        )
    )

    # Not through the debouncer: setup should say what it found now, not in
    # five seconds.
    _sync_issue(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Take the repair down with the integration: it is its only output."""
    ir.async_delete_issue(hass, DOMAIN, ISSUE_DEVICES_WITHOUT_AREA)
    return True


def _devices_without_area(hass: HomeAssistant) -> list[tuple[str, str]]:
    """The offending devices as (name, id), sorted by name."""
    return sorted(
        (device.name_by_user or device.name or device.id, device.id)
        for device in dr.async_get(hass).devices.values()
        if needs_area(device.area_id, device.entry_type, device.disabled_by)
    )


def _sync_issue(hass: HomeAssistant) -> None:
    devices = _devices_without_area(hass)
    if not devices:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_DEVICES_WITHOUT_AREA)
        return

    # Every name is a link to the device page, where Home Assistant's own area
    # picker already lives -- and where the model, the integration and the
    # entity list say *which* room this thing is in. A repair flow with a bare
    # dropdown would have to rebuild all of that to answer the same question.
    # The list is not truncated: a device list is short by nature, and someone
    # with sixty unassigned devices should see sixty lines.
    listed = "\n".join(
        f"- [{name}](/config/devices/device/{device_id})" for name, device_id in devices
    )

    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_DEVICES_WITHOUT_AREA,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_DEVICES_WITHOUT_AREA,
        translation_placeholders={"count": str(len(devices)), "devices": listed},
    )
