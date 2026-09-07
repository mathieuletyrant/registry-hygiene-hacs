"""Turning registry rows into the devices a rule may judge.

This is the part that reads `integration_type`, and the part with the most
moving pieces: a device points at a config entry, the entry names a domain, the
domain's manifest says what kind of thing it is. A mistake anywhere along that
chain reports everything or nothing, and neither looks like a bug from outside.

The registries are faked rather than run, so this stays in the fast suite and
works on both legs of the version matrix. What is being checked is the wiring,
not Home Assistant.
"""

import asyncio
from types import SimpleNamespace

import pytest

import custom_components.registry_hygiene as rh


def device(device_id, domain="light", entry_type=None, disabled_by=None):
    return SimpleNamespace(
        id=device_id,
        name=device_id,
        name_by_user=None,
        area_id=None,
        labels=set(),
        disabled_by=disabled_by,
        entry_type=entry_type,
        primary_config_entry=f"entry_{domain}" if domain else None,
    )


def run(monkeypatch, devices, manifests, asked=None):
    """Resolve `devices` against `manifests`, returning the ids that survive.

    `manifests` maps a domain to its `integration_type`; a domain missing from
    it stands for an integration that failed to load. `asked` collects the
    domains actually looked up.
    """
    hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_entry=lambda entry_id: SimpleNamespace(
                domain=entry_id.removeprefix("entry_")
            )
        )
    )

    monkeypatch.setattr(
        rh.dr,
        "async_get",
        lambda _hass: SimpleNamespace(devices={d.id: d for d in devices}),
    )

    async def _integrations(_hass, domains):
        if asked is not None:
            asked.append(set(domains))
        return {
            domain: (
                SimpleNamespace(integration_type=manifests[domain])
                if domain in manifests
                else ImportError(domain)
            )
            for domain in domains
        }

    monkeypatch.setattr(rh, "async_get_integrations", _integrations)

    return [d.id for d in asyncio.run(rh._async_real_devices(hass))]


def test_a_lamp_survives(monkeypatch):
    assert run(monkeypatch, [device("lamp")], {"light": "device"}) == ["lamp"]


@pytest.mark.parametrize(
    "integration_type", ["system", "hardware", "service", "helper"]
)
def test_what_the_manifest_calls_not_a_thing_is_dropped(monkeypatch, integration_type):
    assert run(monkeypatch, [device("x")], {"light": integration_type}) == []


def test_a_manifest_that_declares_nothing_keeps_its_device(monkeypatch):
    """Home Assistant defaults `integration_type` to "hub", and so must this.

    `bluetooth` and `rpi_power` declare no type at all. Defaulting the other
    way -- treating silence as an exemption -- would drop every unlabelled
    integration on the instance without anything saying so.
    """
    assert run(monkeypatch, [device("hci0")], {"light": "hub"}) == ["hci0"]


def test_an_integration_that_would_not_load_keeps_its_device(monkeypatch):
    """A failed import is not an answer about rooms, so it must not read as
    one. Erring towards reporting is the safe direction: a spurious repair is
    visible and dismissible, a silently dropped device is neither.
    """
    assert run(monkeypatch, [device("mystery")], {}) == ["mystery"]


def test_a_device_belonging_to_no_config_entry_survives(monkeypatch):
    assert run(monkeypatch, [device("orphan", domain=None)], {}) == ["orphan"]


def test_a_service_device_never_reaches_the_manifests(monkeypatch):
    """The registry-only checks run first, so a cloud account costs no lookup.

    Which is the point of the split: on a real instance almost every device is
    settled before anything touches the loader.
    """
    asked = []
    survivors = run(
        monkeypatch,
        [device("cloud", domain="cloud", entry_type="service"), device("lamp")],
        {"light": "device"},
        asked=asked,
    )

    assert survivors == ["lamp"]
    assert asked == [{"light"}]


def test_a_disabled_device_never_reaches_the_manifests(monkeypatch):
    asked = []

    assert run(monkeypatch, [device("old", disabled_by="user")], {}, asked=asked) == []
    assert asked == []


def test_each_domain_is_looked_up_once(monkeypatch):
    """A hundred Zigbee devices share one answer, and one lookup."""
    asked = []
    devices = [device(f"bulb{n}") for n in range(5)] + [device("sw", domain="shelly")]

    run(monkeypatch, devices, {"light": "device", "shelly": "device"}, asked=asked)

    assert asked == [{"light", "shelly"}]
