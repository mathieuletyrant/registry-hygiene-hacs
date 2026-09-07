"""Reconciling the repairs against what the rule currently says.

This is the one piece of logic here that is not a pure rule, and the one that
can do damage: it deletes issues. Two things have to hold. It must not touch
Home Assistant's own repairs, which live in the same registry. And it must not
delete an issue for a device that is *still* offending -- because deleting and
recreating is what would silently un-ignore a device somebody had ignored,
`async_get_or_create` being the only path that leaves `dismissed_version`
alone.
"""

from types import SimpleNamespace

import custom_components.registry_hygiene as rh


def prune(monkeypatch, present, keep):
    """Run the prune over `present`, returning what it asked to delete."""
    deleted = []
    monkeypatch.setattr(
        rh.ir, "async_get", lambda hass: SimpleNamespace(issues=dict.fromkeys(present))
    )
    monkeypatch.setattr(
        rh.ir,
        "async_delete_issue",
        lambda hass, domain, issue_id: deleted.append((domain, issue_id)),
    )
    rh._prune_issues(None, keep=keep)
    return set(deleted)


def test_a_device_still_missing_an_area_keeps_its_issue(monkeypatch):
    """Which is what keeps Ignore meaning something across a refresh."""
    issue = f"{rh.ISSUE_DEVICE_WITHOUT_AREA}_aaa"

    assert prune(monkeypatch, [(rh.DOMAIN, issue)], keep={issue}) == set()


def test_a_device_that_got_an_area_loses_its_issue(monkeypatch):
    issue = f"{rh.ISSUE_DEVICE_WITHOUT_AREA}_aaa"

    assert prune(monkeypatch, [(rh.DOMAIN, issue)], keep=set()) == {(rh.DOMAIN, issue)}


def test_home_assistants_own_repairs_are_left_alone(monkeypatch):
    """They share the registry, and none of them is ours to delete."""
    theirs = ("homeassistant", "deprecated_yaml")

    assert prune(monkeypatch, [theirs], keep=set()) == set()


def test_an_issue_id_we_no_longer_produce_is_cleaned_up(monkeypatch):
    """The rule used to raise one aggregate issue for every device at once.

    Anyone who ran that build has it sitting in their registry, and nothing
    else would ever take it down. Pruning by "ours and not currently wanted",
    rather than by matching the current id shape, handles it for free -- and
    handles the next rename the same way.
    """
    legacy = (rh.DOMAIN, "devices_without_area")

    assert prune(monkeypatch, [legacy], keep=set()) == {legacy}
