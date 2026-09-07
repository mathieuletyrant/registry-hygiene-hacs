"""The rules themselves, with no Home Assistant in the room.

The case that earns the file is the inherited one: a first cut of `needs_area`
looked only at the entity's own `area_id` and flagged nearly every entity on a
well-organised instance, because an area is normally set on the device.
"""

from custom_components.registry_hygiene.rules import needs_area


def test_an_entity_with_its_own_area_is_fine():
    assert not needs_area("cuisine", None, None)


def test_an_area_inherited_from_the_device_is_an_area():
    assert not needs_area(None, "cuisine", None)


def test_an_entity_in_no_area_at_all_is_flagged():
    assert needs_area(None, None, None)


def test_a_disabled_entity_is_never_flagged():
    """It produces no state, so no automation can miss it for want of a room."""
    assert not needs_area(None, None, "user")
