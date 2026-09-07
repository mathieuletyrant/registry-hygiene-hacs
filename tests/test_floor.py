"""What the declared minimum Home Assistant has to provide.

`hacs.json` names the oldest Home Assistant this integration claims to work
on, and `requirements_test_min.txt` exists so the claim is tested rather than
asserted. Every module gets imported here, so a name missing on the floor
fails in CI rather than on somebody's install, and the handful of APIs the
integration genuinely rests on are named -- so raising the floor, or finding
out it has to be raised, says which call did it.
"""

import importlib
import inspect
import json

import pytest

MODULES = ("config_flow", "const", "repairs", "rules")

TRANSLATIONS = (
    "custom_components/registry_hygiene/strings.json",
    "custom_components/registry_hygiene/translations/en.json",
    "custom_components/registry_hygiene/translations/fr.json",
)


@pytest.mark.parametrize("name", MODULES)
def test_every_module_imports(name):
    assert importlib.import_module(f"custom_components.registry_hygiene.{name}")


def test_the_integration_module_imports():
    assert importlib.import_module("custom_components.registry_hygiene")


def test_a_service_device_is_spelled_service():
    """rules.py compares `entry_type` against the bare string, so that the
    rules stay importable without Home Assistant. That only holds while
    `DeviceEntryType` is a StrEnum whose member is exactly "service" -- if it
    ever stops being one, every service device starts getting flagged, quietly
    and everywhere. This is the assertion that would notice.
    """
    from homeassistant.helpers.device_registry import DeviceEntryType

    assert DeviceEntryType.SERVICE == "service"


def test_a_device_entry_carries_what_the_rule_reads():
    from homeassistant.helpers.device_registry import DeviceEntry

    # attrs, not a dataclass -- the annotations are the portable way to ask.
    for field in (
        "area_id",
        "entry_type",
        "disabled_by",
        "name",
        "name_by_user",
        # The second rule reads this one.
        "labels",
    ):
        assert field in DeviceEntry.__annotations__

    # Not in the annotations: it is a plain field on some releases and a
    # derived property on others, so ask the class rather than the shape.
    # This is what says which integration owns the device, and so what kind of
    # thing the device is.
    assert hasattr(DeviceEntry, "primary_config_entry")


def test_an_integration_says_what_kind_of_thing_it_is():
    """`integration_type` is what exempts the machine and the cloud account
    without a deny-list of domains rotting in rules.py. The default matters as
    much as the values: it is "hub", so a manifest that declares nothing stays
    in the list rather than falling out of it.
    """
    from homeassistant.loader import Integration, async_get_integrations

    assert hasattr(Integration, "integration_type")
    assert callable(async_get_integrations)


def test_a_rule_can_be_a_subentry():
    """Subentries are what give a label rule its own row, its own Add button
    and its own delete -- most of the UI a rule builder would otherwise be.
    """
    from homeassistant.config_entries import ConfigFlow, ConfigSubentryFlow

    assert ConfigSubentryFlow is not None
    assert hasattr(ConfigFlow, "async_get_supported_subentry_types")

    # And editing one in place rather than deleting and retyping it: the row
    # only gets a pencil when the flow has a reconfigure step, and these are
    # what that step is built out of.
    for helper in (
        "_get_entry",
        "_get_reconfigure_subentry",
        "async_update_and_abort",
    ):
        assert hasattr(ConfigSubentryFlow, helper)


def test_a_repair_can_carry_a_flow_and_its_data():
    """The Fix button on a label repair. `issue.data` is what the flow is
    handed, and it is where the entity and the labels to write live.
    """
    import inspect

    from homeassistant import data_entry_flow
    from homeassistant.components.repairs import RepairsFlow
    from homeassistant.helpers import issue_registry as ir

    # The steps are the subclass's to define; what the floor has to provide is
    # the base and the `data` that reaches it.
    assert issubclass(RepairsFlow, data_entry_flow.FlowHandler)
    assert "data" in inspect.signature(ir.async_create_issue).parameters


def test_an_entity_s_labels_can_be_written_back():
    """What the Fix button actually does."""
    import inspect

    from homeassistant.helpers.entity_registry import EntityRegistry

    parameters = inspect.signature(EntityRegistry.async_update_entity).parameters

    assert "labels" in parameters


def test_a_label_can_be_picked_and_named():
    """The flow stores a label id and the repair prints the label's name."""
    from homeassistant.helpers import label_registry as lr, selector

    assert selector.LabelSelector(selector.LabelSelectorConfig(multiple=True))
    assert hasattr(lr.LabelRegistry, "async_get_label")


def test_an_entity_entry_carries_what_a_label_rule_reads():
    from homeassistant.helpers.entity_registry import RegistryEntry

    for field in (
        "labels",
        "domain",
        "device_class",
        # The one the integration set, which survives when the user has not
        # overridden it -- most entities only ever have this one.
        "original_device_class",
        "entity_category",
        "disabled_by",
        "device_id",
    ):
        assert field in RegistryEntry.__annotations__


def test_the_entity_registry_announces_its_changes():
    """Subscribed to only when a label rule exists: it is the noisiest event
    on the bus, and with no rule there is nothing it could change.
    """
    from homeassistant.helpers import entity_registry as er

    assert er.EVENT_ENTITY_REGISTRY_UPDATED


def test_the_checkboxes_can_be_built_and_translated():
    """LIST mode with `multiple` is what renders a column of checkboxes rather
    than a dropdown, and `translation_key` is what gives each one a sentence
    instead of its rule id. Both are load-bearing for the options dialog.
    """
    from homeassistant.helpers import selector

    config = selector.SelectSelectorConfig(
        options=["a", "b"],
        multiple=True,
        mode=selector.SelectSelectorMode.LIST,
        translation_key="rules",
    )

    assert selector.SelectSelector(config)


def test_an_options_flow_can_read_its_entry():
    """`self.config_entry` on the base class -- assigning it is deprecated,
    and the flow reads the current selection through it.
    """
    from homeassistant.config_entries import OptionsFlow

    assert hasattr(OptionsFlow, "config_entry")


def test_an_ignored_issue_stays_ignored_when_it_is_raised_again():
    """The repairs are recreated on every refresh, so a device somebody
    ignored would come back on the next registry event if `async_get_or_create`
    reset this. It does not -- its update path replaces everything *except*
    `dismissed_version`. This pins that the concept still exists; the day it
    does not, Ignore silently stops meaning anything.
    """
    from homeassistant.helpers.issue_registry import IssueEntry

    assert "dismissed_version" in IssueEntry.__dataclass_fields__


def test_the_device_registry_announces_its_changes():
    """The repair re-checks on this event; without it, it is only ever as
    fresh as the last restart.
    """
    from homeassistant.helpers import device_registry as dr

    assert dr.EVENT_DEVICE_REGISTRY_UPDATED


def test_the_debouncer_takes_a_cooldown_and_a_function():
    """A restart fires a burst of registry events, and this is what absorbs
    them instead of a hand-rolled timer.
    """
    from homeassistant.helpers.debounce import Debouncer

    parameters = inspect.signature(Debouncer.__init__).parameters

    for name in ("cooldown", "immediate", "function"):
        assert name in parameters
    assert hasattr(Debouncer, "async_shutdown")


def test_the_issue_registry_takes_translated_placeholders():
    """The repair's whole body is a translation plus a list of device links."""
    from homeassistant.helpers import issue_registry as ir

    assert "translation_placeholders" in ir.async_create_issue.__code__.co_varnames
    assert hasattr(ir, "IssueSeverity")


@pytest.mark.parametrize("path", TRANSLATIONS)
def test_every_translation_carries_every_rule(path):
    """A repair whose key is missing renders as the key, and so does a
    checkbox. Adding a rule and forgetting one of three files is the way that
    happens; the rule ids are the translation keys, so this catches it.
    """
    from custom_components.registry_hygiene.const import (
        CONF_DEVICE_CLASSES,
        CONF_INCLUDE_TECHNICAL,
        CONF_KEYWORDS,
        CONF_LABELS,
        ISSUE_MISSING_LABEL,
        SUBENTRY_LABEL_RULE,
    )
    from custom_components.registry_hygiene.rules import ALL_RULES

    with open(path, encoding="utf-8") as handle:
        strings = json.load(handle)

    for rule in ALL_RULES:
        issue = strings["issues"][rule]
        assert "{name}" in issue["title"]
        assert "{device_id}" in issue["description"]
        assert strings["selector"]["rules"]["options"][rule]

    label_rule = strings["issues"][ISSUE_MISSING_LABEL]
    assert "{labels}" in label_rule["title"]
    # No `description` on a fixable issue: hassfest treats it and `fix_flow` as
    # mutually exclusive, because the dialog opens straight into the flow.
    assert "description" not in label_rule

    # So the Fix dialog is where it has to name what it is about to write, or
    # the button asks for consent to something it never said.
    confirm = label_rule["fix_flow"]["step"]["confirm"]
    assert "{labels}" in confirm["title"]
    assert "{labels}" in confirm["description"]
    assert "{entity_id}" in confirm["description"]

    # The subentry dialog: without these the Add button opens a form whose
    # every field is labelled with its own key.
    subentry = strings["config_subentries"][SUBENTRY_LABEL_RULE]
    for field in (
        CONF_KEYWORDS,
        CONF_DEVICE_CLASSES,
        CONF_LABELS,
        CONF_INCLUDE_TECHNICAL,
    ):
        assert subentry["step"]["user"]["data"][field]
    for error in ("matches_nothing", "nothing_to_match"):
        assert subentry["error"][error]

    # Both steps show the same form, so both need its text.
    assert subentry["step"]["reconfigure"]["data"] == subentry["step"]["user"]["data"]
    assert subentry["abort"]["reconfigure_successful"]


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
