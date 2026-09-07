"""Registry Hygiene: surface valid-but-badly-filed devices as Repairs."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, issue_registry as ir
from homeassistant.helpers.debounce import Debouncer
from homeassistant.loader import async_get_integrations

from .const import DOMAIN, OPTION_RULES
from .rules import DEFAULT_RULES, broken_rules, is_a_real_device

_LOGGER = logging.getLogger(__name__)

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
    enabled = frozenset(entry.options.get(OPTION_RULES, DEFAULT_RULES))

    async def _check(_event=None) -> None:
        await _async_sync_issues(hass, enabled)

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
    entry.async_on_unload(entry.add_update_listener(_async_reload))

    # Not through the debouncer: setup should say what it found now, not in
    # five seconds.
    await _async_sync_issues(hass, enabled)
    return True


async def _async_reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Turning a rule on or off takes effect on the spot.

    Reloading is all it takes: setup re-reads the options and re-reconciles, so
    switching a rule off takes its repairs down with it.
    """
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Leave the repairs standing.

    Deliberately *not* the place to take them down. A reload -- which is how an
    options change applies -- unloads and sets up again, and deleting an issue
    drops its `dismissed_version` with it. Tearing them down here would silently
    un-ignore every device the user had ignored, every time they touched the
    settings. `async_remove_entry` is where they go, and that only fires when
    the integration is actually removed.
    """
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Take the repairs down with the integration: they are its only output."""
    _prune_issues(hass, keep=set())


async def _async_integration_types(hass: HomeAssistant, domains: set[str]) -> dict:
    """What kind of integration each domain declares itself to be.

    Fetched in one call rather than per device, and keyed by domain rather than
    by device, because a hundred Zigbee devices share one answer.
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


def _domain_of(hass: HomeAssistant, device) -> str | None:
    entry_id = device.primary_config_entry
    if not entry_id:
        return None
    entry = hass.config_entries.async_get_entry(entry_id)
    return entry.domain if entry else None


async def _async_real_devices(hass: HomeAssistant) -> list:
    """Every device a rule is allowed to have an opinion about."""
    candidates = [
        device
        for device in dr.async_get(hass).devices.values()
        # Registry-only and cheap, so it runs before any manifest is looked up
        # and settles most of them.
        if device.disabled_by is None
        and device.entry_type != dr.DeviceEntryType.SERVICE
    ]

    types = await _async_integration_types(
        hass, {domain for device in candidates if (domain := _domain_of(hass, device))}
    )

    return [
        device
        for device in candidates
        # "hub" is what Home Assistant itself falls back to for a manifest that
        # says nothing, and it is the answer that keeps a device in the list.
        if is_a_real_device(
            device.entry_type,
            device.disabled_by,
            types.get(_domain_of(hass, device), "hub"),
        )
    ]


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


async def _async_sync_issues(hass: HomeAssistant, enabled: frozenset[str]) -> None:
    wanted = {
        f"{rule}_{device.id}": (rule, device)
        for device in await _async_real_devices(hass)
        for rule in broken_rules(enabled, device.area_id, device.labels)
    }

    _prune_issues(hass, keep=set(wanted))

    for issue_id, (rule, device) in wanted.items():
        # One issue per device per rule, so that Home Assistant's own Ignore
        # button means "not this one" rather than "none of them". The residue
        # no rule can decide -- a phone, a dongle -- is exactly what that
        # button is for, and it costs no configuration of ours.
        #
        # ponytail: an instance mid-migration with a hundred unfiled devices
        # gets a hundred repairs. If that turns up, the fix is to fall back to
        # one aggregate issue above some threshold, not to paginate.
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=rule,
            translation_placeholders={
                "name": _device_name(device),
                "device_id": device.id,
            },
        )
