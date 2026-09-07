"""Registry Hygiene: surface valid-but-badly-filed devices as Repairs."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, issue_registry as ir
from homeassistant.helpers.debounce import Debouncer
from homeassistant.loader import async_get_integrations

from .rules import needs_area

_LOGGER = logging.getLogger(__name__)

DOMAIN = "registry_hygiene"
ISSUE_DEVICE_WITHOUT_AREA = "device_without_area"

# The device registry churns while integrations set up: a restart fires a burst
# of events over a few seconds. The check is cheap but not free a hundred times
# over, and without a cooldown the repairs would flicker their way to the right
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
        await _async_sync_issues(hass)

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
    await _async_sync_issues(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Take the repairs down with the integration: they are its only output."""
    _prune_issues(hass, keep=set())
    return True


async def _async_integration_types(hass: HomeAssistant, domains: set[str]) -> dict:
    """What kind of integration each domain declares itself to be.

    Fetched in one call rather than per device, and by domain rather than by
    device, because a hundred Zigbee devices share one answer.
    """
    if not domains:
        return {}

    return {
        domain: integration.integration_type
        for domain, integration in (
            await async_get_integrations(hass, domains)
        ).items()
        # An integration that failed to load is not an answer about rooms.
        if not isinstance(integration, Exception)
    }


async def _async_devices_without_area(hass: HomeAssistant) -> list:
    """The offending devices, sorted by the name they are shown under."""
    devices = [
        device
        for device in dr.async_get(hass).devices.values()
        # Cheap and registry-only, so it runs before the manifests are looked
        # up and decides most of them.
        if device.disabled_by is None
        and device.entry_type != dr.DeviceEntryType.SERVICE
        and not device.area_id
    ]

    entries = hass.config_entries
    domains = {
        entry.domain
        for device in devices
        if device.primary_config_entry
        and (entry := entries.async_get_entry(device.primary_config_entry))
    }
    types = await _async_integration_types(hass, domains)

    def _integration_type(device) -> str:
        entry = (
            entries.async_get_entry(device.primary_config_entry)
            if device.primary_config_entry
            else None
        )
        # "hub" is what Home Assistant itself falls back to for a manifest that
        # says nothing, and it is the answer that keeps a device in the list.
        return types.get(entry.domain, "hub") if entry else "hub"

    return sorted(
        (
            device
            for device in devices
            if needs_area(
                device.area_id,
                device.entry_type,
                device.disabled_by,
                _integration_type(device),
            )
        ),
        key=_device_name,
    )


def _device_name(device) -> str:
    return device.name_by_user or device.name or device.id


def _prune_issues(hass: HomeAssistant, keep: set[str]) -> None:
    """Drop every issue of ours that is not in `keep`.

    Reconciling rather than deleting-then-creating is what makes Ignore stick:
    `async_get_or_create` leaves `dismissed_version` alone when the issue is
    already there, so a device somebody ignored stays ignored across restarts
    and refreshes. Deleting it first would silently un-ignore it.
    """
    for domain, issue_id in list(ir.async_get(hass).issues):
        if domain == DOMAIN and issue_id not in keep:
            ir.async_delete_issue(hass, DOMAIN, issue_id)


async def _async_sync_issues(hass: HomeAssistant) -> None:
    devices = await _async_devices_without_area(hass)
    issue_ids = {f"{ISSUE_DEVICE_WITHOUT_AREA}_{device.id}" for device in devices}

    _prune_issues(hass, keep=issue_ids)

    for device in devices:
        # One issue per device, so that Home Assistant's own Ignore button
        # means "not this one" rather than "none of them". The residue this
        # rule cannot decide -- a phone, a dongle -- is exactly what that
        # button is for, and it costs no configuration of ours.
        #
        # ponytail: an instance mid-migration with a hundred unfiled devices
        # gets a hundred repairs. If that turns up, the fix is to fall back to
        # one aggregate issue above some threshold, not to paginate.
        ir.async_create_issue(
            hass,
            DOMAIN,
            f"{ISSUE_DEVICE_WITHOUT_AREA}_{device.id}",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_DEVICE_WITHOUT_AREA,
            translation_placeholders={
                "name": _device_name(device),
                "device_id": device.id,
            },
        )
