# Registry Hygiene — Home Assistant integration

Checks the device registry against a set of hygiene rules and reports what it
finds as Repairs. It reads the registry and writes issues; it talks to no
device, no network, no cloud.

**Devices, not entities**, and that was not the starting point. An entity
inherits its area from its device, so the entity-level rule reported one
unassigned light twelve times — once per entity it owns — and every one of the
twelve was fixed by the same single click. On the author's instance it produced
175 findings covering roughly a dozen real problems. The device grain is the
same information, deduplicated, and each line is actionable. Entities are no
longer read at all.

## Shape

| File | What it holds |
| ---- | ------------- |
| `rules.py` | The rules, as pure functions, plus `is_a_real_device` — the gate they all sit behind — and which of them default on. **Never imports homeassistant** — that is the point of the file, and what keeps a rule arguable without a running instance. It compares `entry_type` against the bare string `"service"`; `tests/test_floor.py` pins that value so the import can stay out. |
| `__init__.py` | Reads the registry, calls the rules, reconciles the issues, and re-checks on `EVENT_DEVICE_REGISTRY_UPDATED` behind a `Debouncer` — a restart fires a burst of those. |
| `config_flow.py` | One entry, one confirmation; the options flow (a checkbox per built-in check, and nothing else in it ever); and the label-rule subentry flow. |
| `const.py` | The names the flows, the rules and the entry point share, so `config_flow.py` and `repairs.py` can import them without pulling the registries and the loader in behind them. |
| `repairs.py` | The Fix button on a label repair, and nothing else. Discovered through `dependencies: ["repairs"]` in the manifest. |
| `scripts/make_icon.py` | Draws `icons/`. Nine rounded squares; the drawing is the source. |
| `strings.json` + `translations/` | The text of every repair. `strings.json` and `translations/en.json` are the same file; keep `fr.json` in step. |

A new rule is a function in `rules.py`, a caller in `__init__.py`, and an entry
under `issues` in all three translation files. If a rule needs `hass` to decide,
it does not belong in `rules.py`.

## Two grains, on purpose

Areas are checked on **devices**, label rules on **entities**. Not an
inconsistency to tidy up: an entity inherits its area from its device, so the
area question is only ever about the device — but a label policy is written
against entity ids, and a device has none. `rules.py` has a gate for each
grain, `is_a_real_device` and `is_a_real_entity`.

A label rule is satisfied by the label sitting on the entity **or on its
device**, which is what makes the device-grain use case work anyway.

## Four things not to undo

**One issue per device, and reconcile — never delete then recreate.**
`async_get_or_create` is the only path that leaves `dismissed_version` alone,
so recreating a still-offending device's issue preserves the user's Ignore.
`_prune_issues` deletes only what is no longer wanted, and `tests/test_issues.py`
is what says so. Ignore is the whole ignore-list feature; there is no options
flow because that button already is one.

**`async_unload_entry` must not delete the issues.** A reload — which is how
an options change applies — unloads and sets up again, and deleting an issue
takes `dismissed_version` with it. Tearing them down there would un-ignore
every device the user had ignored, every time they touched the settings.
`async_remove_entry` is the hook that fires only on real removal, and that is
where they go.

**A label rule has two matchers in OR, and both earn their place.** A device
class is what the source integration set, so it finds an entity whose name says
nothing -- class `motion`, called `hall_detection`. A word finds what no class
expresses -- `linky`, `interrupteur`, `homelab` -- because those are facts about
the installation, not the hardware. Dropping either one was tried and was wrong
both times. Words are plain substrings, matched against the entity id *and* the
slugified device name: an entity id is built from the device name once and then
frozen, so a renamed device is only findable through the name.

**Only the label repair is fixable.** A rule already says which labels to
apply, so its flow is one button. An area is a judgment, and a dropdown inside
a repair dialog would be a worse copy of the one on the device page — that is
why `_async_sync_issues` passes `data=None` for the device checks and lets
`is_fixable` follow from it.

**`config`/`diagnostic` entities are filtered per rule, not globally.** An
earlier cut filtered them everywhere, which made `battery`, `firmware`,
`update` -> `maintenance` impossible to write — a rule about exactly those
entities.

**`hub` is not exempt.** It is also Home Assistant's fallback for a manifest
that declares no `integration_type`, so exempting it would quietly exempt
everything unlabelled — `bluetooth` and `rpi_power` among them — along with
every Hue bridge, which is a box on a shelf. `tests/test_rules.py` pins both
edges.

## Tests

Python 3.14.2 — the system `python3` is too old. `uv venv --python 3.14.2`,
`uv pip install -r requirements_test.txt`, `.venv/bin/pytest tests/ -q`.
`uv pip` and not `pip`, because a uv venv ships no pip of its own.

Requirements are pinned exactly, not `>=` — the comment at the top of
`requirements_test.txt` says what the unpinned version does. Two files:

| File | What it is |
| ---- | ---------- |
| `requirements_test.txt` | the environment to develop in, and CI's main job |
| `requirements_test_min.txt` | the oldest HA `hacs.json` claims to support, so the claim is tested |

Raising the floor means editing `requirements_test_min.txt` and `hacs.json`
together, plus the Python paired with it in `.github/workflows/tests.yaml`.
`tests/test_floor.py` fails if the first two disagree, and names the APIs the
floor has to have.

## Lint

`uv pip install -r requirements_lint.txt`, then `.venv/bin/ruff check .`. CI
runs the same and it has to be clean. Configuration is in `pyproject.toml`; the
rules that are off are off for a stated reason.

CI runs on pull requests based on `main` **or** on a `claude/**` branch. That
second one is not decoration: the trigger filters on the *base* branch, so a
pull request stacked on another one would otherwise get no checks at all —
which is not the same as passing, and reads exactly like it.

`ruff format` is **not** run.

## Releasing

CalVer. Bump `version` in `custom_components/registry_hygiene/manifest.json`,
merge that, then dispatch the **Release** workflow with the same version — it
refuses to run if the manifest disagrees.
