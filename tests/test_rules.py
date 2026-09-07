"""The rule itself, with no Home Assistant in the room.

The case that earns the file is the one that moved the rule from entities to
devices: an entity inherits its area from its device, so checking entities
reported one unassigned light twelve times over -- once per entity it owns --
and the fix for all twelve was the same single click.
"""

from custom_components.registry_hygiene.rules import needs_area


def test_a_device_with_an_area_is_fine():
    assert not needs_area("cuisine", None, None)


def test_a_device_in_no_area_is_flagged():
    assert needs_area(None, None, None)


def test_an_empty_string_is_not_an_area():
    """The registry stores None, but a placeholder should not sneak past."""
    assert needs_area("", None, None)


def test_a_service_is_never_flagged():
    """A cloud account is nowhere, and nowhere is the right answer for it.

    "service" is `DeviceEntryType.SERVICE`; test_floor.py pins the value so
    rules.py can compare against the string without importing homeassistant.
    """
    assert not needs_area(None, "service", None)


def test_a_disabled_device_is_never_flagged():
    """It shows nowhere and produces nothing, so an area changes nothing."""
    assert not needs_area(None, None, "user")


def test_a_service_that_somehow_has_an_area_is_still_fine():
    assert not needs_area("cuisine", "service", None)
