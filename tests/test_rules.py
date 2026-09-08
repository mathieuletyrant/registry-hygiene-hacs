"""The rules themselves, with no Home Assistant in the room.

Two things carry the file. `is_a_real_device` is the gate every rule sits
behind, and its edges are what stop the checks from being noise -- the
tempting mistake is to widen the exemptions until nothing is ever reported.
`broken_rules` is the part that has to respect what the user turned on.
"""

from custom_components.registry_hygiene.const import (
    CONF_DEVICE_CLASSES,
    CONF_INCLUDE_TECHNICAL,
    CONF_KEYWORDS,
    CONF_LABELS,
)
from custom_components.registry_hygiene.rules import (
    ALL_RULES,
    DEFAULT_RULES,
    RULE_AREA,
    RULE_FLOOR,
    RULE_LABEL,
    areas_without_floor,
    broken_rules,
    is_a_real_device,
    is_a_real_entity,
    missing_labels,
)


def real(entry_type=None, disabled_by=None, integration_type="device"):
    """A device the gate lets through, unless an argument says otherwise."""
    return is_a_real_device(entry_type, disabled_by, integration_type)


def test_an_ordinary_device_is_a_real_device():
    assert real()


def test_a_service_is_not():
    """A cloud account is nowhere, and nowhere is the right answer for it.

    "service" is `DeviceEntryType.SERVICE`; test_floor.py pins the value so
    rules.py can compare against the string without importing homeassistant.
    """
    assert not real(entry_type="service")


def test_a_disabled_device_is_not():
    """It shows nowhere and produces nothing, so filing it changes nothing."""
    assert not real(disabled_by="user")


def test_home_assistant_talking_about_itself_is_not():
    """`homeassistant` and `cloud` both declare `system`."""
    assert not real(integration_type="system")


def test_the_machine_it_runs_on_is_not():
    """`raspberry_pi` declares `hardware`."""
    assert not real(integration_type="hardware")


def test_a_helper_is_not():
    assert not real(integration_type="helper")


def test_a_hub_is():
    """A Hue bridge is a box on a shelf. This is the edge that matters most:
    `hub` is also what Home Assistant falls back to for a manifest that
    declares nothing, so exempting it would silently exempt everything
    unlabelled -- `bluetooth` and `rpi_power` among them.
    """
    assert real(integration_type="hub")


def test_a_phone_is_and_that_is_the_known_limit():
    """`mobile_app` declares `device`, honestly, because a phone is one.

    No flag Home Assistant maintains separates a phone from a lamp, so the
    rules do not try. This is the case the per-device repair exists for:
    Ignore it once, and Home Assistant remembers.
    """
    assert real(integration_type="device")


def test_a_filed_device_breaks_nothing():
    assert broken_rules(ALL_RULES, "cuisine", {"security"}) == []


def test_each_rule_reports_what_it_is_about():
    assert broken_rules(ALL_RULES, None, {"security"}) == [RULE_AREA]
    assert broken_rules(ALL_RULES, "cuisine", set()) == [RULE_LABEL]
    assert broken_rules(ALL_RULES, None, set()) == [RULE_AREA, RULE_LABEL]


def test_an_empty_string_is_not_an_area():
    """The registry stores None, but a placeholder should not sneak past."""
    assert broken_rules(ALL_RULES, "", {"security"}) == [RULE_AREA]


def test_a_rule_that_is_off_reports_nothing():
    assert broken_rules({RULE_AREA}, None, set()) == [RULE_AREA]
    assert broken_rules(set(), None, set()) == []


def test_labels_are_off_by_default_and_areas_are_not():
    """Home Assistant has an opinion about rooms and none about labels, so one
    of these is a defect on any instance and the other is only a defect once
    its owner has decided on a scheme. Flipping this default would greet every
    new install with a repair per device.
    """
    assert broken_rules(DEFAULT_RULES, None, set()) == [RULE_AREA]


UPSTAIRS = [("salon", "ground"), ("bureau", None), ("jardin", "")]


def test_no_floors_means_the_feature_is_unused():
    """The gate, and the reason this rule can default on where labels cannot.
    An instance that has never created a floor is not untidy.
    """
    assert areas_without_floor(ALL_RULES, False, UPSTAIRS) == []


def test_one_floor_is_a_decision_and_the_rest_are_omissions():
    assert areas_without_floor(ALL_RULES, True, UPSTAIRS) == ["bureau", "jardin"]


def test_floors_created_but_nothing_assigned_still_reports():
    """Deriving the gate from the areas would go silent for exactly the person
    this helps most: floors made, none used yet.
    """
    assert areas_without_floor(ALL_RULES, True, [("salon", None)]) == ["salon"]


def test_the_floor_rule_is_on_by_default_and_can_be_turned_off():
    assert areas_without_floor(DEFAULT_RULES, True, [("salon", None)]) == ["salon"]
    assert areas_without_floor(set(), True, [("salon", None)]) == []
    assert RULE_FLOOR in DEFAULT_RULES



def test_an_enabled_entity_can_be_judged():
    assert is_a_real_entity(None)


def test_a_disabled_entity_cannot():
    assert not is_a_real_entity("integration")


def rule(
    keywords=("mouvement", "contact"),
    device_classes=(),
    labels=("securite",),
    technical=False,
):
    return {
        CONF_KEYWORDS: list(keywords),
        CONF_DEVICE_CLASSES: list(device_classes),
        CONF_LABELS: list(labels),
        CONF_INCLUDE_TECHNICAL: technical,
    }


def missing(
    r=None,
    entity_id="binary_sensor.hall_mouvement",
    device_class=None,
    entity_category=None,
    labels=frozenset(),
    device_labels=frozenset(),
):
    return missing_labels(
        r or rule(), entity_id, device_class, entity_category, labels, device_labels
    )


def test_a_matching_entity_is_missing_the_label():
    assert missing() == ["securite"]


def test_a_word_matches_anywhere_in_the_id():
    """Which is the whole reason keywords beat device classes here: Home
    Assistant already puts the class in the id -- `sensor.salon_temperature` --
    so one matcher reaches both naming conventions and classes.
    """
    assert missing(rule(keywords=["temperature"]), "sensor.salon_temperature")
    assert missing(rule(keywords=["linky"]), "sensor.linky_intensite")


def test_a_non_matching_entity_is_left_alone():
    assert missing(entity_id="light.cuisine") == []


def test_a_device_class_recognises_what_no_word_would():
    """The case that earns the second signal: the class is right, the name
    says nothing. An integration sets `motion`; the entity is called
    `detection`.
    """
    by_class = rule(keywords=[], device_classes=["motion", "occupancy"])

    assert missing(by_class, "binary_sensor.hall_detection", "motion") == ["securite"]
    assert missing(by_class, "binary_sensor.hall_detection", "door") == []


def test_either_signal_is_enough_and_neither_overrules_the_other():
    """A rule carrying both is one rule with two ways of being recognised."""
    both = rule(keywords=["mouvement"], device_classes=["motion"])

    assert missing(both, "binary_sensor.hall_mouvement", None) == ["securite"]
    assert missing(both, "binary_sensor.hall_detection", "motion") == ["securite"]
    assert missing(both, "light.cuisine", "illuminance") == []


def test_a_word_does_not_reach_the_device_s_name():
    """Searching the device name as well was tried and taken out. A Zigbee
    motion sensor is a multi-sensor: a device called "Capteur mouvement
    bureau" made the keyword `mouvement` match its temperature, illuminance
    and battery entities too -- a systematic false positive on nearly every
    sensor, traded for the occasional renamed device that the device class
    signal already covers.
    """
    assert missing(entity_id="sensor.bureau_temperature") == []


def test_the_label_on_the_entity_satisfies_the_rule():
    assert missing(labels={"securite"}) == []


def test_the_label_on_the_device_satisfies_it_too():
    """Which is what lets somebody label a multi-sensor once instead of
    labelling each of its three entities. Without this, the tidier style would
    produce a repair per entity for a device that is perfectly filed.
    """
    assert missing(device_labels={"securite"}) == []


def test_only_the_labels_actually_absent_are_reported():
    """A rule asking for two, one of which is already there."""
    both = rule(labels=["confort", "lumiere"], keywords=["lampadaire"])

    assert missing(both, "light.lampadaire", labels={"confort"}) == ["lumiere"]


def test_plumbing_is_out_of_scope_by_default():
    """A motion detector's battery sensor has no business carrying
    `securite` because the motion sensor does.
    """
    assert missing(entity_id="sensor.hall_mouvement_battery",
                   entity_category="diagnostic") == []


def test_a_rule_can_opt_into_plumbing():
    """And a real policy has exactly one such rule: `battery`, `firmware`,
    `update`, `backup` -> maintenance is about nothing else. Filtering
    diagnostics globally, as an earlier cut did, made that rule impossible to
    write.
    """
    maintenance = rule(
        keywords=["battery"], labels=["maintenance"], technical=True
    )

    assert missing(maintenance, "sensor.hall_battery",
                   entity_category="diagnostic") == ["maintenance"]


def test_the_domain_prefix_is_part_of_the_id():
    """Which is how a rule gets scoped to a domain without a field for it, and
    why automations, scripts and helpers are already reachable: they are
    entities, and their id starts with what they are.
    """
    only_automations = rule(keywords=["automation."], labels=["revue"])

    assert missing(only_automations, "automation.alarme_absence") == ["revue"]
    assert missing(only_automations, "binary_sensor.hall_mouvement") == []
