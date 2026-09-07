"""The names the flows, the rules and the entry point share.

Separate from `__init__.py` so that `config_flow.py` and `repairs.py` can
import them without pulling the package -- and with it the registries and the
loader -- into their import path. `rules.py` imports them too, which is safe
for the same reason nothing else here is: this module imports nothing.
"""

from __future__ import annotations

DOMAIN = "registry_hygiene"

OPTION_RULES = "rules"

# One subentry per label rule. Subentries are Home Assistant's own answer to
# "let the user add several of these", so the Add button, the list of rules and
# the delete button all come for free -- which is most of what a rule builder
# would otherwise have to be.
SUBENTRY_LABEL_RULE = "label_rule"

CONF_KEYWORDS = "keywords"
CONF_LABELS = "labels"
CONF_INCLUDE_TECHNICAL = "include_technical"

ISSUE_MISSING_LABEL = "entity_missing_label"
