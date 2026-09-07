"""Pure hygiene rules. Never imports homeassistant, so the fast test loop is
free of it -- and so a rule can be argued about without a running instance.
"""

from __future__ import annotations

# `integration_type`, from the integration's own manifest. Home Assistant
# maintains these, which is the whole reason to lean on them rather than on a
# deny-list of domains that would rot here.
#
# `system` is Home Assistant talking about itself, `hardware` is the machine it
# runs on, `service` is a subscription, `helper` is a template. None of them is
# an object you could walk up to and point at.
#
# What is deliberately *not* in this set is `hub` -- which is also the default
# for a manifest that says nothing, so it covers far more than real bridges.
# A Hue bridge is a box on a shelf and belongs in a room.
NOT_IN_A_ROOM = frozenset({"system", "hardware", "service", "helper"})


def needs_area(area_id, entry_type, disabled_by, integration_type):
    """True when a device ought to have an area and has none.

    Devices rather than entities, which is not where this started. An entity
    inherits its area from its device, so a single unassigned light reported
    every one of its twelve entities -- `light`, `identify`, `update`, RSSI --
    as twelve separate problems, all fixed by one click on the device. The
    entity-level rule was reporting a dozen devices a hundred and seventy-five
    times.

    Three exemptions, all read off flags Home Assistant maintains itself:

    `entry_type == "service"` is how Home Assistant marks a "device" that is
    not one -- a cloud account, a subscription, a logical bridge. The string is
    `DeviceEntryType.SERVICE`, a StrEnum; `tests/test_floor.py` pins the value
    so this file can stay free of the import.

    `integration_type` in `NOT_IN_A_ROOM`, above.

    A disabled device appears nowhere and produces nothing, so an area would
    change nothing about it.

    What survives is *mostly* physical, and there the rule stops. It does not
    reach zero on a real instance and cannot: a phone moves, a Bluetooth dongle
    is inside the machine, an integration invents a device to hang a button
    off. Every one of those declares itself a device, honestly, because it is
    one. That residue is a human decision taken once per device -- which is
    what the per-device repair is for, so Home Assistant's own Ignore button
    can hold the answer.
    """
    return (
        disabled_by is None
        and entry_type != "service"
        and integration_type not in NOT_IN_A_ROOM
        and not area_id
    )
