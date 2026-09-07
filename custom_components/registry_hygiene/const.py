"""The two names both the flow and the entry point need.

Separate from `__init__.py` only so that `config_flow.py` can import them
without pulling the package -- and with it the registries and the loader --
into the config flow's import path.
"""

from __future__ import annotations

DOMAIN = "registry_hygiene"
OPTION_RULES = "rules"
