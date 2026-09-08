"""Registry Hygiene: surface valid-but-badly-filed devices as Repairs."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    floor_registry as fr,
    issue_registry as ir,
    label_registry as lr,
)
from homeassistant.helpers.debounce import Debouncer
from homeassistant.loader import async_get_integrations

from .const import DOMAIN, ISSUE_MISSING_LABEL, OPTION_RULES, SUBENTRY_LABEL_RULE
from .rules import (
    DEFAULT_RULES,
    RULE_EMPTY_FLOOR,
    RULE_FLOOR,
    areas_without_floor,
    broken_rules,
    floors_without_area,
    is_a_real_device,
    is_a_real_entity,
    missing_labels,
)

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
    label_rules = {
        subentry_id: subentry.data
        for subentry_id, subentry in entry.subentries.items()
        if subentry.subentry_type == SUBENTRY_LABEL_RULE
    }

    async def _check(_event=None) -> None:
        await _async_sync_issues(hass, enabled, label_rules)

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
    if label_rules:
        # Only with rules to check: an entity registry event fires for every
        # rename and every state-less change on the instance, and subscribing
        # to that to answer a question nobody asked would be the noisiest thing
        # here by an order of magnitude.
        entry.async_on_unload(
            hass.bus.async_listen(
                er.EVENT_ENTITY_REGISTRY_UPDATED, _on_device_registry_update
            )
        )

    if enabled & {RULE_FLOOR, RULE_EMPTY_FLOOR}:
        # Assigning the floor is done on the area page, which moves the area
        # registry and nothing else -- without these the repair would sit there
        # after the very edit that fixed it. Creating the first floor matters
        # too: that is what opens the gate in `areas_without_floor`. Both
        # registries hold a dozen rows and change by hand, so unlike the entity
        # registry there is no burst to be afraid of.
        for signal in (ar.EVENT_AREA_REGISTRY_UPDATED, fr.EVENT_FLOOR_REGISTRY_UPDATED):
            entry.async_on_unload(
                hass.bus.async_listen(signal, _on_device_registry_update)
            )

    # Adding or removing a subentry goes through `_async_update_entry`, which
    # fires this, so a new rule applies without anyone reloading anything.
    entry.async_on_unload(entry.add_update_listener(_async_reload))

    # Not through the debouncer: setup should say what it found now, not in
    # five seconds.
    await _async_sync_issues(hass, enabled, label_rules)
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


def _entity_name(entity, device) -> str:
    """The device's name and the entity's, because the entity's alone is not a
    name.

    On a multi-sensor the entity names are `Manipulation`, `Personne`,
    `Véhicule`, `Animal` -- accurate, generic, and identical across every such
    device on the instance. A repairs page showing four rows called
    "Manipulation" says nothing about which four things need attention.
    """
    own = entity.name or entity.original_name
    if device is None:
        return own or entity.entity_id
    return f"{_device_name(device)} · {own}" if own else _device_name(device)


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


def _label_violations(hass: HomeAssistant, label_rules: dict) -> dict:
    """Every (rule, entity) pair where the entity is missing the rule's labels.

    One pass over the entity registry rather than one per rule: an instance has
    a handful of rules and thousands of entities.
    """
    if not label_rules:
        return {}

    devices = dr.async_get(hass)
    labels = lr.async_get(hass)
    found = {}

    def _name(label_id: str) -> str:
        label = labels.async_get_label(label_id)
        return label.name if label else label_id

    for entity in er.async_get(hass).entities.values():
        if not is_a_real_entity(entity.disabled_by):
            continue

        device = devices.async_get(entity.device_id) if entity.device_id else None
        device_labels = device.labels if device else frozenset()

        for subentry_id, rule in label_rules.items():
            wanted = missing_labels(
                rule,
                entity.entity_id,
                entity.device_class or entity.original_device_class,
                entity.entity_category,
                entity.labels,
                device_labels,
            )
            if not wanted:
                continue

            found[f"{ISSUE_MISSING_LABEL}_{subentry_id}_{entity.id}"] = (
                ISSUE_MISSING_LABEL,
                {
                    "name": _entity_name(entity, device),
                    "entity_id": entity.entity_id,
                    "labels": ", ".join(_name(label) for label in wanted),
                },
                # What the fix flow needs to do the work, and nothing more: it
                # re-reads the entity itself, so a registry that moved between
                # the repair being raised and the button being pressed does not
                # get written back stale. The device is there so the flow can
                # offer to label it instead -- which on a multi-sensor is the
                # answer, since one label there settles every one of its
                # entities at once.
                {
                    "entity_id": entity.entity_id,
                    "labels": wanted,
                    "device_id": device.id if device else None,
                },
            )

    return found


async def _async_sync_issues(
    hass: HomeAssistant, enabled: frozenset[str], label_rules: dict
) -> None:
    wanted = {
        f"{rule}_{device.id}": (
            rule,
            {"name": _device_name(device), "device_id": device.id},
            # No fix data: which room a device is in is not something this can
            # work out, which is why that repair sends you to the device page
            # instead of offering a button.
            None,
        )
        for device in await _async_real_devices(hass)
        for rule in broken_rules(enabled, device.area_id, device.labels)
    }
    areas = ar.async_get(hass)
    floors = fr.async_get(hass).async_list_floors()
    pairs = [(area.id, area.floor_id) for area in areas.async_list_areas()]

    wanted |= {
        f"{RULE_FLOOR}_{area_id}": (
            RULE_FLOOR,
            {
                "name": areas.async_get_area(area_id).name,
                "area_id": area_id,
            },
            # Which floor a room is on is a judgment, exactly as its area is.
            None,
        )
        for area_id in areas_without_floor(enabled, bool(floors), pairs)
    }
    by_id = {floor.floor_id: floor for floor in floors}
    wanted |= {
        f"{RULE_EMPTY_FLOOR}_{floor_id}": (
            RULE_EMPTY_FLOOR,
            {"name": by_id[floor_id].name},
            # Nothing to decide, but nothing to press either: which rooms are
            # upstairs is a judgment, and floors are assigned from the area
            # side anyway.
            None,
        )
        for floor_id in floors_without_area(
            enabled, [floor.floor_id for floor in floors], pairs
        )
    }
    wanted |= _label_violations(hass, label_rules)

    _prune_issues(hass, keep=set(wanted))

    for issue_id, (translation_key, placeholders, fix_data) in wanted.items():
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
            # Fixable only where there is nothing left to decide. A label
            # rule already says which labels to apply, so the flow is one
            # button; an area is a judgment, and a dropdown in a repair dialog
            # would be a worse version of the one on the device page.
            is_fixable=fix_data is not None,
            data=fix_data,
            severity=ir.IssueSeverity.WARNING,
            translation_key=translation_key,
            translation_placeholders=placeholders,
        )
