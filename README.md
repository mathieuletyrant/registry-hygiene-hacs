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
  page, where you set the area once and all of its entities inherit it. **On by
  default.**
- 🏷️ **Devices with no label** — the same, for the labels nothing else will
  remind you about. **Off by default**, because Home Assistant has no opinion
  about labels and neither should a fresh install.
- 📐 **Your own label rules** — *anything called `volet` or `chauffage` must be
  labelled `confort`*. Add as many as you like from the integration page, and
  these ones come with a **Fix** button.

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

One dialog, behind **Configure** on the integration card: a checkbox per check.
That is all it will ever hold, because the two other things a settings page is
normally for are already covered without it.

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

## 📐 Label rules

For when you do have a policy. Press **Add label rule** on the integration
page:

| Field | |
| --- | --- |
| Words | `volet`, `chauffage`, `seche_serviette` |
| Required labels | `confort` |
| Include config and diagnostic entities | off |

Every entity whose id contains one of those words, and which carries neither
`confort` itself nor on its device, gets a repair — with a **Fix** button that
applies the label. The rule already says which label; there is nothing to
choose, so there is no dropdown, just a confirmation naming what it will write.

**Words, not patterns.** A real seven-rule policy turned out to be alternations
of plain substrings every time, and the two that looked like regular
expressions were each already covered by a literal in the same rule. Substrings
need no validating, cannot backtrack over a few thousand entity ids, and are a
field anyone can fill in.

They are matched against the **entity id**, which is also why there is no
separate device-class matcher: Home Assistant already builds the class into the
id for most integrations, so `temperature` reaches `sensor.salon_temperature`
and `battery` reaches `sensor.hall_battery`.

**Entities here, devices above**, on purpose. An entity inherits its area from
its device, so the area question is only ever about the device — but a rule
about `securite` has to be able to leave a detector's battery sensor alone
while a rule about `maintenance` is about nothing else. That is the last
checkbox: technical entities are out of scope unless the rule says otherwise.

A rule whose words match nothing on your instance is refused with a message,
because a rule that never fires looks exactly like a rule everything passes.

## 🩺 What a report looks like

One repair per device per check, titled with the device's name. It re-checks
whenever the device registry changes, so assigning an area makes the repair
vanish in front of you rather than at the next restart. Nothing here ever
blocks anything.

## 🤝 Contributing

Python 3.14.2, `uv venv --python 3.14.2`, then
`uv pip install -r requirements_test.txt` and `.venv/bin/pytest tests/ -q`.
`ruff check .` has to come back clean — `requirements_lint.txt` pins it.

## 📄 Licence

MIT.
