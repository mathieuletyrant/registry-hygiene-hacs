"""Pure hygiene rules. Never imports homeassistant, so the fast test loop is
free of it -- and so a rule can be argued about without a running instance.
"""

from __future__ import annotations

from .const import (
    CONF_DEVICE_CLASSES,
    CONF_INCLUDE_TECHNICAL,
    CONF_KEYWORDS,
    CONF_LABELS,
)

RULE_AREA = "device_without_area"
RULE_LABEL = "device_without_label"
RULE_FLOOR = "area_without_floor"

ALL_RULES = (RULE_AREA, RULE_LABEL, RULE_FLOOR)

# Area is on for everyone; labels are not. Home Assistant has an opinion about
# rooms -- `area_id` is in the data model, voice assistants and area-scoped
# automations reason with it, so "no area" is wrong on any instance. It has no
# opinion about labels: they are free-form tags with no schema, and an instance
# with none of them is not untidy, it just does not use the feature. That rule
# only means something once its owner has decided on a scheme, which is a thing
# only its owner can say.
# Floor is on by default too, and for the same reason as area rather than in
# spite of the labels argument: it gates itself. An instance with no floors is
# not using the feature and the rule returns nothing, so defaulting it on costs
# those instances precisely one thing -- a checkbox they never see fire. The
# moment somebody creates a floor they have decided on a scheme, and an area
# left off it is an omission rather than a choice.
#
# Only new entries pick this up. An existing entry has its list already stored
# in options, so the rule arrives when its owner next opens the settings, not
# as a surprise burst of repairs on upgrade.
DEFAULT_RULES = (RULE_AREA, RULE_FLOOR)

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


def areas_without_floor(enabled, has_floors, areas):
    """Which areas are on no floor, given `areas` as (area_id, floor_id) pairs.

    A third grain, and the only honest one for this question: an area is not a
    device and has no device to answer for it. It stays cheap because the count
    is the count of rooms -- a dozen, where devices are hundreds -- so this
    cannot flood the way an entity-grain rule can.

    `has_floors` is the gate, and it is why this rule can default on where the
    label rule cannot. Home Assistant has no opinion about whether an instance
    uses floors, so an instance with none is not untidy. But creating one *is*
    the decision, and from there an area left off a floor breaks the same
    things a missing area breaks: floor-scoped targeting, `floor_id` in a
    template, "turn off the lights upstairs".

    Deliberately read off the floor registry rather than off these pairs. A
    user who has created floors and assigned no area yet is the person this is
    most useful to, and deriving the gate from the pairs would be silent
    exactly then.
    """
    if RULE_FLOOR not in enabled or not has_floors:
        return []

    return [area_id for area_id, floor_id in areas if not floor_id]



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


def missing_labels(
    rule, entity_id, device_class, entity_category, labels, device_labels
):
    """Which of the rule's labels this entity ought to carry and does not.

    Two matchers, in OR, because they fail in opposite directions.

    A **device class** is set by the integration that created the entity, so it
    is a fact about the hardware rather than about how somebody named things.
    Where it exists it is the better signal: an entity of class `motion` may
    perfectly well be called `binary_sensor.hall_detection`, and no keyword
    would find it.

    A **keyword** reaches everything a device class cannot say. On the policy
    this was built against, half the concepts had no class at all -- `linky`,
    `interrupteur`, `seche_serviette`, `homelab`, `zigbee2mqtt` -- because they
    are facts about that installation, not about the hardware. Plain substrings
    rather than patterns: every rule in that policy was an alternation of
    literals, and the two that looked like regular expressions were each
    already covered by a literal beside them. Substrings need no validating and
    cannot backtrack over thousands of ids.

    Keywords search the `entity_id` and nothing else. Searching the device's
    name as well was tried, to catch a device renamed after its entities were
    created, and had to come out: a Zigbee motion sensor is a multi-sensor, so
    a device called "Capteur mouvement bureau" made the keyword `mouvement`
    match its temperature, illuminance and battery entities too. That is a
    systematic false positive on nearly every sensor, traded for an occasional
    true one -- and the occasional one is what the device class signal is for.

    The domain prefix is part of the `entity_id`, so `automation.` on its own
    scopes a rule to every automation -- which is also why automations, scripts
    and helpers need nothing special to be reachable.

    The label counts whether it sits on the entity or on its device, so both
    styles work: label the multi-sensor once and its three entities are
    covered, or label the single `motion` entity of a camera and leave the
    video feed out of it.
    """
    if entity_category is not None and not rule.get(CONF_INCLUDE_TECHNICAL):
        return []

    by_keyword = any(
        keyword in entity_id for keyword in rule.get(CONF_KEYWORDS, ())
    )
    by_class = device_class is not None and device_class in rule.get(
        CONF_DEVICE_CLASSES, ()
    )

    # Either signal is enough. They fail in opposite directions, so a rule that
    # carries both is not two rules -- it is one rule with two ways of being
    # recognised, and neither overrules the other.
    if not (by_keyword or by_class):
        return []

    carried = set(labels) | set(device_labels)
    return [label for label in rule[CONF_LABELS] if label not in carried]
