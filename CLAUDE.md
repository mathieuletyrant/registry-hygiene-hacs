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
| `rules.py` | The rules, as pure functions. **Never imports homeassistant** — that is the point of the file, and what keeps a rule arguable without a running instance. It compares `entry_type` against the bare string `"service"`; `tests/test_floor.py` pins that value so the import can stay out. |
| `__init__.py` | Reads the registry, calls the rules, syncs the issues, and re-checks on `EVENT_DEVICE_REGISTRY_UPDATED` behind a `Debouncer` — a restart fires a burst of those. |
| `config_flow.py` | One entry, one confirmation, nothing to fill in. |
| `strings.json` + `translations/` | The text of every repair. `strings.json` and `translations/en.json` are the same file; keep `fr.json` in step. |

A new rule is a function in `rules.py`, a caller in `__init__.py`, and an entry
under `issues` in all three translation files. If a rule needs `hass` to decide,
it does not belong in `rules.py`.

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
