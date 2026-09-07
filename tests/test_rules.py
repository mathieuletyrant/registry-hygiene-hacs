"""The rules themselves, with no Home Assistant in the room.

Two things carry the file. `is_a_real_device` is the gate every rule sits
behind, and its edges are what stop the checks from being noise -- the
tempting mistake is to widen the exemptions until nothing is ever reported.
`broken_rules` is the part that has to respect what the user turned on.
"""

from custom_components.registry_hygiene.rules import (
    ALL_RULES,
    DEFAULT_RULES,
    RULE_AREA,
    RULE_LABEL,
    broken_rules,
    is_a_real_device,
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
