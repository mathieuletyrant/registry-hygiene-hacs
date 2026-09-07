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
- 📐 **Your own label rules** — *anything of class `motion`, or called `sirene`,
  must be labelled `securite`*. Add as many as you like from the integration
  page, and these ones come with a **Fix** button.

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
| Device classes | `motion`, `occupancy`, `smoke`, `door`, `window` |
| Words | `sirene`, `alarme`, `clavier` |
| Required labels | `securite` |
| Include config and diagnostic entities | off |

**Either signal is enough**, and a rule usually wants both, because they fail
in opposite directions.

A **device class** is set by the integration that created the entity — a fact
about the hardware, not about how anything was named. Where it exists it is the
better of the two: an entity of class `motion` may perfectly well be called
`binary_sensor.hall_detection`, and no word would ever find it. Only the
classes your instance actually uses are offered, read off the registry rather
than off a list of every class Home Assistant defines.

A **word** reaches everything a device class cannot say. `linky`,
`interrupteur`, `seche_serviette`, `homelab`, `zigbee2mqtt` have no class and
never will: they are facts about your installation, not about the hardware.
Plain substrings, not patterns — a real seven-rule policy turned out to be
alternations of literals every time, and substrings need no validating and
cannot backtrack over thousands of entity ids.

Words are matched against the **entity id**, and only that. Searching the
device's name too was tried, to catch a device renamed after its entities were
created, and had to come out: a Zigbee motion sensor is a multi-sensor, so a
device called "Capteur mouvement bureau" made the word `mouvement` match its
temperature, illuminance and battery entities as well. A device class is the
right tool for the renamed device, and it does not spill.

The domain prefix is part of the id, so `automation.` on its own — dot
included — scopes a rule to every automation, which is also why automations,
scripts and helpers need nothing special to be reachable.

Every entity a rule recognises, and which carries none of its labels — neither
itself nor on its device — gets a repair, with a **Fix** button that applies
them. The rule already says which labels, so there is nothing to choose about
*what* — only about *where*, and the button asks:

> **Label the device — Salon capteur mouvement (9 entities)**
> Label only this entity

**Take the device, usually.** Words match the entity id, and Home Assistant
builds that id out of the device's name — so a detector called "Salon capteur
mouvement" puts `mouvement` into `sensor.salon_capteur_mouvement_temperature`
just as surely as into its occupancy entity. On one instance fifteen repairs
were three devices. A rule counts a label on the device as carried, so one
press settles all of them.

**Entities here, devices above**, on purpose. An entity inherits its area from
its device, so the area question is only ever about the device — but a rule
about `securite` has to leave a detector's battery sensor alone while a rule
about `maintenance` is about nothing else. That is the last checkbox: technical
entities are out of scope unless the rule says otherwise.

A rule whose words match nothing on your instance is refused with a message,
because a rule that never fires looks exactly like a rule everything passes.
A rejected submission comes back with everything you typed still in it.

Rules are edited in place from the same page — the row's pencil — and changing
one brings its repairs in line straight away, including taking down the ones it
no longer asks for.

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
