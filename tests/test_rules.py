"""The rule itself, with no Home Assistant in the room.

Two cases carry the file. One is the move from entities to devices: an entity
inherits its area from its device, so checking entities reported one unassigned
light twelve times over -- once per entity it owns -- and the fix for all twelve
was the same single click.

The other is `integration_type`, and what it does *not* exempt. The set is
deliberately narrow, and the tests below pin both edges of it -- because the
tempting mistake is to widen it until the rule reports nothing.
"""

from custom_components.registry_hygiene.rules import needs_area


def device(area_id=None, entry_type=None, disabled_by=None, integration_type="device"):
    """A device the rule would flag, unless an argument says otherwise."""
    return needs_area(area_id, entry_type, disabled_by, integration_type)


def test_a_device_with_an_area_is_fine():
    assert not device(area_id="cuisine")


def test_a_device_in_no_area_is_flagged():
    assert device()


def test_an_empty_string_is_not_an_area():
    """The registry stores None, but a placeholder should not sneak past."""
    assert device(area_id="")


def test_a_service_is_never_flagged():
    """A cloud account is nowhere, and nowhere is the right answer for it.

    "service" is `DeviceEntryType.SERVICE`; test_floor.py pins the value so
    rules.py can compare against the string without importing homeassistant.
    """
    assert not device(entry_type="service")


def test_a_disabled_device_is_never_flagged():
    """It shows nowhere and produces nothing, so an area changes nothing."""
    assert not device(disabled_by="user")


def test_home_assistant_talking_about_itself_is_not_in_a_room():
    """`homeassistant` and `cloud` both declare `system`."""
    assert not device(integration_type="system")


def test_the_machine_it_runs_on_is_not_in_a_room():
    """`raspberry_pi` declares `hardware`."""
    assert not device(integration_type="hardware")


def test_a_helper_is_not_in_a_room():
    assert device(integration_type="helper") is False


def test_a_hub_is_in_a_room():
    """A Hue bridge is a box on a shelf. This is the edge that matters most:
    `hub` is also what Home Assistant falls back to for a manifest that
    declares nothing, so exempting it would silently exempt everything
    unlabelled -- `bluetooth` and `rpi_power` among them.
    """
    assert device(integration_type="hub")


def test_a_phone_is_still_flagged_and_that_is_the_known_limit():
    """`mobile_app` declares `device`, honestly, because a phone is one.

    No flag Home Assistant maintains separates a phone from a lamp, so the rule
    does not try. This is the case the per-device repair exists for: Ignore it
    once, and Home Assistant remembers.
    """
    assert device(integration_type="device")
