# 🧹 Registry Hygiene

A Home Assistant integration that keeps an eye on your **registry**, and tells
you where it has gone untidy.

Home Assistant never complains about a device that works but is badly filed.
Nothing breaks — until an automation reasons by room, or a voice assistant is
asked to turn off the kitchen and finds half of it missing.

This integration checks the registry against a set of rules and reports what it
finds under **Settings → Repairs**, alongside Home Assistant's own.

## ✨ What you get

- 🏠 **Devices with no area** — one repair per device, linking straight to its
  page, where you set the area once and all of its entities inherit it.

More rules may follow; this list is what exists today rather than what is
planned.

## 👻 Isn't this Spook?

No — they lint in opposite directions, and they compose.

[Spook](https://github.com/frenck/spook) finds **dead references**: an
automation, a script, a scene, a dashboard or the energy panel pointing at an
entity, a device or an area that no longer exists. Config → registry.

Registry Hygiene finds **bad filing**: the device exists, it works, it is
simply nowhere. Registry → quality. Spook's `empty_areas` is even the exact
mirror of this — it finds rooms with nothing in them, this finds things in no
room.

Run both.

## 📦 Installation

### HACS

Add this repository as a custom repository (category **Integration**), install
**Registry Hygiene**, restart Home Assistant, then add the integration from
**Settings → Devices & services**.

### Manual

Copy `custom_components/registry_hygiene` into your Home Assistant
`config/custom_components/`, restart, then add the integration.

## ⚙️ Configuration

None, and there is nothing to add later either — the two things a settings
page would normally be for are already covered.

**Filtering** is read off flags Home Assistant maintains itself: devices it
marks as a service (a cloud account, a subscription), disabled ones, and
integrations that declare themselves `system`, `hardware`, `service` or
`helper` — Home Assistant talking about itself, the machine it runs on, a
template. No list of domains for anyone to keep current.

**The rest is you.** That filtering does not reach zero and cannot: a phone
moves, a Bluetooth dongle is inside the machine, an integration invents a
device to hang a button off. Each of those honestly declares itself a device,
because it is one. So they get a repair each, and you press **Ignore** —
Home Assistant remembers, per device, forever. That is the ignore list, and it
needed no code.

## 🩺 What a report looks like

One repair per device, titled with its name. It re-checks whenever the device
registry changes, so assigning an area makes the repair vanish in front of you
rather than at the next restart. Nothing here ever blocks anything.

## 🤝 Contributing

Python 3.14.2, `uv venv --python 3.14.2`, then
`uv pip install -r requirements_test.txt` and `.venv/bin/pytest tests/ -q`.
`ruff check .` has to come back clean — `requirements_lint.txt` pins it.

## 📄 Licence

MIT.
