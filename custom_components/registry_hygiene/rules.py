"""Pure hygiene rules. Never imports homeassistant, so the fast test loop is
free of it -- and so a rule can be argued about without a running instance.
"""

from __future__ import annotations

from .const import CONF_INCLUDE_TECHNICAL, CONF_KEYWORDS, CONF_LABELS

RULE_AREA = "device_without_area"
RULE_LABEL = "device_without_label"

ALL_RULES = (RULE_AREA, RULE_LABEL)

# Area is on for everyone; labels are not. Home Assistant has an opinion about
# rooms -- `area_id` is in the data model, voice assistants and area-scoped
# automations reason with it, so "no area" is wrong on any instance. It has no
# opinion about labels: they are free-form tags with no schema, and an instance
# with none of them is not untidy, it just does not use the feature. That rule
# only means something once its owner has decided on a scheme, which is a thing
# only its owner can say.
DEFAULT_RULES = (RULE_AREA,)

# `integration_type`, from the integration's own manifest. Home Assistant
# maintains these, which is the whole reason to lean on them rather than on a
# deny-list of domains that would rot here.
#
# `system` is Home Assistant talking about itself, `hardware` is the machine it
# runs on, `service` is a subscription, `helper` is a template. None of them is
# an object you could walk up to and point at, so none of them wants a room or
# a label.
#
# What is deliberately *not* in this set is `hub` -- which is also the default
# for a manifest that says nothing, so it covers far more than real bridges.
# A Hue bridge is a box on a shelf and belongs in a room.
NOT_A_REAL_DEVICE = frozenset({"system", "hardware", "service", "helper"})


def is_a_real_device(entry_type, disabled_by, integration_type):
    """True when this row in the registry stands for a physical object.

    Shared by every rule, because the exemptions are about the device rather
    than about what is being asked of it: a cloud account needs a label no more
    than it needs a room.

    `entry_type == "service"` is how Home Assistant marks a "device" that is
    not one -- a cloud account, a subscription, a logical bridge. The string is
    `DeviceEntryType.SERVICE`, a StrEnum; `tests/test_floor.py` pins the value
    so this file can stay free of the import.

    A disabled device appears nowhere and produces nothing.

    What survives is *mostly* physical, and there this stops. It does not reach
    zero on a real instance and cannot: a phone moves, a Bluetooth dongle is
    inside the machine, an integration invents a device to hang a button off.
    Every one of those declares itself a device, honestly, because it is one.
    That residue is a human decision taken once per device -- which is what the
    per-device repair is for, so Home Assistant's own Ignore button can hold
    the answer.
    """
    return (
        disabled_by is None
        and entry_type != "service"
        and integration_type not in NOT_A_REAL_DEVICE
    )


def broken_rules(enabled, area_id, labels):
    """Which of the enabled rules this device breaks, in `ALL_RULES` order.

    Devices rather than entities, which is not where this started. An entity
    inherits its area from its device, so a single unassigned light reported
    every one of its twelve entities -- `light`, `identify`, `update`, RSSI --
    as twelve separate problems, all fixed by one click on the device. The
    entity-level rule was reporting a dozen devices a hundred and seventy-five
    times.
    """
    broken = []
    if RULE_AREA in enabled and not area_id:
        broken.append(RULE_AREA)
    if RULE_LABEL in enabled and not labels:
        broken.append(RULE_LABEL)
    return broken



def is_a_real_entity(disabled_by):
    """True when a label rule is allowed to have an opinion about an entity.

    Only disabled entities are out, and unconditionally: they produce nothing,
    so nothing selects them.

    `config` and `diagnostic` entities are deliberately *not* filtered here,
    although an earlier cut did filter them. A rule about `securite` has no
    business with a battery sensor -- but a rule about `maintenance` is about
    nothing else, and `battery`, `firmware`, `update` and `backup` are exactly
    the entities it wants. Whether the technical ones count is a property of
    the rule, not of the registry, so it lives on the rule.
    """
    return disabled_by is None


def missing_labels(rule, entity_id, entity_category, labels, device_labels):
    """Which of the rule's labels this entity ought to carry and does not.

    Keywords against the `entity_id`, not a pattern language. A real policy --
    seven rules, on a real instance -- turned out to be alternations of plain
    substrings every time; the two that looked like regular expressions were
    each already covered by a literal in the same rule. Substrings need no
    validating, cannot backtrack catastrophically over a few thousand entity
    ids, and are a field anyone can fill in.

    The `entity_id` rather than the friendly name because it is the stable one,
    and because Home Assistant builds it out of the device class for most
    integrations: `sensor.salon_temperature`, `sensor.x_battery`,
    `binary_sensor.y_motion`. A keyword reaches those without a second matcher
    for device classes.

    The label counts whether it sits on the entity or on its device, so both
    styles work: label the multi-sensor once and its three entities are
    covered, or label the single `motion` entity of a camera and leave the
    video feed out of it.
    """
    if entity_category is not None and not rule.get(CONF_INCLUDE_TECHNICAL):
        return []

    if not any(keyword in entity_id for keyword in rule[CONF_KEYWORDS]):
        return []

    carried = set(labels) | set(device_labels)
    return [label for label in rule[CONF_LABELS] if label not in carried]
