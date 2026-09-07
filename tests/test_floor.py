"""What the declared minimum Home Assistant has to provide.

`hacs.json` names the oldest Home Assistant this integration claims to work
on, and `requirements_test_min.txt` exists so the claim is tested rather than
asserted. Every module gets imported here, so a name missing on the floor
fails in CI rather than on somebody's install, and the handful of APIs the
integration genuinely rests on are named -- so raising the floor, or finding
out it has to be raised, says which call did it.
"""

import importlib
import json

import pytest

MODULES = ("config_flow", "rules")


@pytest.mark.parametrize("name", MODULES)
def test_every_module_imports(name):
    assert importlib.import_module(f"custom_components.registry_hygiene.{name}")


def test_the_integration_module_imports():
    assert importlib.import_module("custom_components.registry_hygiene")


def test_the_issue_registry_takes_translated_placeholders():
    """The repair's whole body is a translation plus a list of entity ids."""
    from homeassistant.helpers import issue_registry as ir

    assert "translation_placeholders" in ir.async_create_issue.__code__.co_varnames
    assert hasattr(ir, "IssueSeverity")


def test_an_entity_entry_carries_an_area_and_a_device():
    """`needs_area` reads both, and inherits one from the other."""
    from homeassistant.helpers.entity_registry import RegistryEntry

    # attrs, not a dataclass -- the annotations are the portable way to ask.
    for field in ("area_id", "device_id", "disabled_by"):
        assert field in RegistryEntry.__annotations__


def test_the_declared_floor_is_the_one_the_tests_run_against():
    """hacs.json and requirements_test_min.txt have to say the same thing, or
    the job proving the floor is proving a different one.
    """
    with open("hacs.json", encoding="utf-8") as handle:
        declared = json.load(handle)["homeassistant"]

    with open("requirements_test_min.txt", encoding="utf-8") as handle:
        pinned = [
            line.split("==")[1].strip()
            for line in handle
            if line.startswith("homeassistant==")
        ]

    assert pinned == [declared]
