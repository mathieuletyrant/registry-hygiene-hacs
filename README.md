# 🧹 Registry Hygiene

A Home Assistant integration that keeps an eye on your **entity registry**, and
tells you where it has gone untidy.

Home Assistant never complains about an entity that works but is badly filed:
no area, no sensible name, orphaned from every device. Nothing breaks — until
an automation reasons by room, or a voice assistant is asked to turn off the
kitchen and finds half of it missing.

This integration checks the registry against a set of rules and reports what it
finds under **Settings → Repairs**, alongside Home Assistant's own.

## ✨ What you get

- 🏠 **Entities with no area** — neither their own, nor one inherited from
  their device.

More rules are coming; this list is what exists today rather than what is
planned.

## 📦 Installation

### HACS

Add this repository as a custom repository (category **Integration**), install
**Registry Hygiene**, restart Home Assistant, then add the integration from
**Settings → Devices & services**.

### Manual

Copy `custom_components/registry_hygiene` into your Home Assistant
`config/custom_components/`, restart, then add the integration.

## ⚙️ Configuration

None. Setting it up runs the checks; there is nothing to fill in.

## 🩺 What a report looks like

A repair, not a notification: it stays until the registry is tidy, disappears
on its own once it is, and never blocks anything.

## 🤝 Contributing

Python 3.14.2, `uv venv --python 3.14.2`, then
`uv pip install -r requirements_test.txt` and `.venv/bin/pytest tests/ -q`.
`ruff check .` has to come back clean — `requirements_lint.txt` pins it.

## 📄 Licence

MIT.
