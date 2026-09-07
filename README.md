# 🧹 Registry Hygiene

A Home Assistant integration that keeps an eye on your **registry**, and tells
you where it has gone untidy.

Home Assistant never complains about a device that works but is badly filed.
Nothing breaks — until an automation reasons by room, or a voice assistant is
asked to turn off the kitchen and finds half of it missing.

This integration checks the registry against a set of rules and reports what it
finds under **Settings → Repairs**, alongside Home Assistant's own.

## ✨ What you get

- 🏠 **Devices with no area** — every name is a link straight to the device
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

None, and that is a design goal rather than an omission. The rule exempts the
devices Home Assistant itself marks as a service — a cloud account, a
subscription, a bridge — and disabled ones. What is left is physical, and a
physical object is somewhere, so there is no structural false positive for you
to filter out by hand.

## 🩺 What a report looks like

A repair, not a notification: it stays until the registry is tidy, disappears
on its own once it is, and never blocks anything. It re-checks whenever the
device registry changes, so assigning an area makes it update in front of you
rather than at the next restart.

## 🤝 Contributing

Python 3.14.2, `uv venv --python 3.14.2`, then
`uv pip install -r requirements_test.txt` and `.venv/bin/pytest tests/ -q`.
`ruff check .` has to come back clean — `requirements_lint.txt` pins it.

## 📄 Licence

MIT.
