"""Pure hygiene rules. Never imports homeassistant, so the fast test loop is
free of it -- and so a rule can be argued about without a running instance.
"""

from __future__ import annotations


def needs_area(area_id, entry_type, disabled_by):
    """True when a device ought to have an area and has none.

    Devices rather than entities, which is not where this started. An entity
    inherits its area from its device, so a single unassigned light reported
    every one of its twelve entities -- `light`, `identify`, `update`, RSSI --
    as twelve separate problems, all fixed by one click on the device. The
    entity-level rule was reporting a dozen devices a hundred and seventy-five
    times.

    Two exemptions, both read off flags Home Assistant maintains itself rather
    than a list of integrations somebody here would have to keep current:

    `entry_type == "service"` is how Home Assistant marks a "device" that is
    not one -- a cloud account, a subscription, a logical bridge. It is
    nowhere, and that is the correct answer for it. The string is
    `DeviceEntryType.SERVICE`, a StrEnum; `tests/test_floor.py` pins the value
    so this file can stay free of the import.

    A disabled device appears nowhere and produces nothing, so an area would
    change nothing about it.

    What is left is a physical object, and a physical object is somewhere. That
    is why this rule needs no configuration to be usable on someone else's
    instance: there is no structural false positive left to filter out.
    """
    return disabled_by is None and entry_type != "service" and not area_id
