"""Walking the entity registry for the label rules.

The rule itself is pure and tested next door; what is checked here is the walk
around it -- that a rule reaches the entity's device for the label, that
plumbing entities are skipped before any rule sees them, and that the issue ids
keep two rules about the same entity apart.

The registries are faked rather than run, so this stays in the fast suite and
works on both legs of the version matrix.
"""

from types import SimpleNamespace

import pytest

import custom_components.registry_hygiene as rh
from custom_components.registry_hygiene.const import (
    CONF_DEVICE_CLASSES,
    CONF_INCLUDE_TECHNICAL,
    CONF_KEYWORDS,
    CONF_LABELS,
)

MOTION_RULE = {
    CONF_KEYWORDS: ["mouvement"],
    CONF_DEVICE_CLASSES: [],
    CONF_LABELS: ["label_security"],
    CONF_INCLUDE_TECHNICAL: False,
}


def entity(
    entity_id="binary_sensor.hall_mouvement",
    labels=frozenset(),
    entity_category=None,
    device_id=None,
    device_class=None,
):
    return SimpleNamespace(
        id=entity_id.replace(".", "_"),
        entity_id=entity_id,
        name=None,
        original_name="Hall",
        entity_category=entity_category,
        disabled_by=None,
        labels=labels,
        device_id=device_id,
        device_class=None,
        original_device_class=device_class,
    )


@pytest.fixture
def violations(monkeypatch):
    """Run `_label_violations` over faked registries."""

    def run(entities, rules, device_labels=frozenset(), device_name=None):
        monkeypatch.setattr(
            rh.er,
            "async_get",
            lambda _h: SimpleNamespace(entities={e.id: e for e in entities}),
        )
        monkeypatch.setattr(
            rh.dr,
            "async_get",
            lambda _h: SimpleNamespace(
                async_get=lambda _id: SimpleNamespace(
                    labels=device_labels,
                    name=device_name,
                    name_by_user=None,
                    id="dev1",
                )
            ),
        )
        monkeypatch.setattr(
            rh.lr,
            "async_get",
            lambda _h: SimpleNamespace(
                async_get_label=lambda label_id: SimpleNamespace(name="Security")
            ),
        )
        return rh._label_violations(None, rules)

    return run


def test_a_matching_entity_without_the_label_is_reported(violations):
    found = violations([entity()], {"sub1": MOTION_RULE})

    assert len(found) == 1
    (translation_key, placeholders, fix_data), = found.values()
    assert translation_key == "entity_missing_label"
    assert placeholders["entity_id"] == "binary_sensor.hall_mouvement"
    # No device on this one, so the entity's own name has to stand alone.
    assert placeholders["name"] == "Hall"
    # The label's name, not the id the selector stored -- "Security" is what
    # the user called it, `label_security` is bookkeeping.
    assert placeholders["labels"] == "Security"
    # And the ids, not the names, for the flow that will write them back.
    assert fix_data == {
        "entity_id": "binary_sensor.hall_mouvement",
        "labels": ["label_security"],
        "device_id": None,
    }


def test_the_label_on_the_entity_s_device_counts(violations):
    found = violations(
        [entity(device_id="dev1")],
        {"sub1": MOTION_RULE},
        device_labels={"label_security"},
    )

    assert found == {}


def test_plumbing_never_reaches_a_rule(violations):
    plumbing = entity(entity_category="diagnostic")

    assert violations([plumbing], {"sub1": MOTION_RULE}) == {}


def test_two_rules_about_one_entity_stay_apart(violations):
    """Their issue ids carry the subentry, so ignoring one leaves the other."""
    other = dict(MOTION_RULE, labels=["label_indoor"])
    found = violations([entity()], {"sub1": MOTION_RULE, "sub2": other})

    assert len(found) == 2
    assert all("sub1" in key or "sub2" in key for key in found)


def test_no_rules_means_no_walk(violations):
    """The registry is not read at all when nothing would be asked of it."""
    assert violations([entity()], {}) == {}


def test_a_device_class_reaches_an_entity_no_word_would(violations):
    """The second signal, through the walk: the class is set, the name is not
    saying anything.
    """
    by_class = dict(MOTION_RULE, keywords=[], device_classes=["motion"])
    found = violations(
        [entity(entity_id="binary_sensor.hall_detection", device_class="motion")],
        {"sub1": by_class},
    )

    assert len(found) == 1


def test_a_secondary_entity_of_a_matched_device_is_left_alone(violations):
    """The regression that sent 34 repairs at somebody's climate sensors.

    A Zigbee motion sensor is a multi-sensor. While the device's name was
    searched too, `mouvement` matched "Capteur mouvement bureau" and every
    entity hanging off it -- temperature included, already correctly labelled
    `climat`, and asked for `securite`.
    """
    found = violations(
        [entity(entity_id="sensor.bureau_temperature", device_id="dev1")],
        {"sub1": MOTION_RULE},
        device_name="Capteur mouvement bureau",
    )

    assert found == {}


def test_the_title_names_the_device_as_well(violations):
    """Four rows called "Manipulation" name nothing. The entity names on a
    multi-sensor are generic and identical across every one of them.
    """
    found = violations(
        [entity(device_id="dev1")],
        {"sub1": MOTION_RULE},
        device_name="Entrée mouvement",
    )

    placeholders = next(iter(found.values()))[1]

    assert placeholders["name"] == "Entrée mouvement · Hall"
