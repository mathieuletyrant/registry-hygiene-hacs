"""Pure hygiene rules. Never imports homeassistant, so the fast test loop is
free of it -- and so a rule can be argued about without a running instance.
"""

from __future__ import annotations


def needs_area(entity_area_id, device_area_id, disabled_by):
    """True when an entity has no effective area.

    An entity's area is its own `area_id`, or the one it inherits from its
    device. Checking only `area_id` flags almost every entity on a
    well-organised instance, because areas are usually set on the device.
    """
    return disabled_by is None and not entity_area_id and not device_area_id
