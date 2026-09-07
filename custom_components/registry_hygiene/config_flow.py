"""Config flow: one instance, and a checkbox per rule behind Configure."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er, label_registry as lr, selector

from .const import (
    CONF_DEVICE_CLASSES,
    CONF_INCLUDE_TECHNICAL,
    CONF_KEYWORDS,
    CONF_LABELS,
    DOMAIN,
    OPTION_RULES,
    SUBENTRY_LABEL_RULE,
)
from .rules import ALL_RULES, DEFAULT_RULES, is_a_real_entity


class RegistryHygieneConfigFlow(ConfigFlow, domain=DOMAIN):
    """One entry, created by clicking through a single confirmation."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Confirm, then create the single entry. There is nothing to ask.

        The rules are options rather than data: they are the part that changes
        after installation, and asking about them here would put a decision in
        front of somebody who has not yet seen a single finding.
        """
        if user_input is None:
            return self.async_show_form(step_id="user")
        return self.async_create_entry(title="Registry Hygiene", data={})

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """The Configure button on the integration card is this method."""
        return RegistryHygieneOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """The Add label rule button on the integration card is this method."""
        return {SUBENTRY_LABEL_RULE: LabelRuleSubentryFlow}


class RegistryHygieneOptionsFlow(OptionsFlow):
    """Which rules run.

    Only the rules. No exclusion filters by domain or by integration, on
    purpose: the per-device Ignore button already does that job, and does it
    better -- it answers about the one device in front of you rather than about
    a category, and Home Assistant is the one remembering.
    """

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Show the checkboxes, or store what came back from them."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(OPTION_RULES, list(DEFAULT_RULES))

        # A multi-select in LIST mode is what renders as a column of
        # checkboxes; the translation_key is what gives each one a sentence
        # instead of its rule id.
        checkboxes = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=list(ALL_RULES),
                multiple=True,
                mode=selector.SelectSelectorMode.LIST,
                translation_key=OPTION_RULES,
            )
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {vol.Required(OPTION_RULES, default=list(current)): checkboxes}
            ),
        )



def _matchable(hass: HomeAssistant) -> tuple[list[str], list[str]]:
    """What a rule could match on this instance: entity ids, and the device
    classes actually in use.

    The classes are read off the registry rather than off a table of every
    class Home Assistant defines: the table would need maintaining as core
    grows classes, and would offer choices matching nothing here.
    """
    entity_ids = []
    classes = set()

    for entity in er.async_get(hass).entities.values():
        if not is_a_real_entity(entity.disabled_by):
            continue
        entity_ids.append(entity.entity_id)
        if found := entity.device_class or entity.original_device_class:
            classes.add(found)

    return entity_ids, sorted(classes)


class LabelRuleSubentryFlow(ConfigSubentryFlow):
    """One rule: entities recognised by a device class or by a word carry
    these labels.

    A subentry rather than a list inside the options, because that is what
    gives the rule its own row, its own Add button and its own delete -- the
    UI a rule builder would otherwise have to grow, already written and already
    familiar.
    """

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Ask what the rule recognises, and which labels it requires."""
        errors: dict[str, str] = {}
        entity_ids, classes = _matchable(self.hass)

        if user_input is not None:
            keywords = sorted(
                {
                    word.strip().lower()
                    for word in user_input.get(CONF_KEYWORDS, [])
                    if word.strip()
                }
            )
            device_classes = sorted(set(user_input.get(CONF_DEVICE_CLASSES, [])))

            if not keywords and not device_classes:
                errors["base"] = "nothing_to_match"
            # A rule that matches nothing does not look like a mistake from
            # outside -- it looks exactly like a rule everything already
            # satisfies. This form is the only place that can say otherwise.
            # Device classes need no such check: they were picked from what
            # this instance has.
            elif not device_classes and not any(
                keyword in entity_id for keyword in keywords for entity_id in entity_ids
            ):
                errors[CONF_KEYWORDS] = "matches_nothing"
            else:
                data = {
                    CONF_KEYWORDS: keywords,
                    CONF_DEVICE_CLASSES: device_classes,
                    CONF_LABELS: user_input[CONF_LABELS],
                    CONF_INCLUDE_TECHNICAL: user_input.get(
                        CONF_INCLUDE_TECHNICAL, False
                    ),
                }
                return self.async_create_entry(
                    title=_rule_title(self.hass, data), data=data
                )

        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=vol.Schema(
                {
                    # A free-text multi-select is the chip input: type a word,
                    # press enter, type the next one.
                    vol.Optional(CONF_KEYWORDS): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[], multiple=True, custom_value=True
                        )
                    ),
                    vol.Optional(CONF_DEVICE_CLASSES): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=classes, multiple=True)
                    ),
                    vol.Required(CONF_LABELS): selector.LabelSelector(
                        selector.LabelSelectorConfig(multiple=True)
                    ),
                    vol.Optional(
                        CONF_INCLUDE_TECHNICAL, default=False
                    ): selector.BooleanSelector(),
                }
            ),
        )


def _rule_title(hass: HomeAssistant, data: dict[str, Any]) -> str:
    """What the rule's row reads as: `Sécurité \u2190 contact, mouvement, fumee`."""
    registry = lr.async_get(hass)
    names = [
        found.name if (found := registry.async_get_label(label)) else label
        for label in data[CONF_LABELS]
    ]

    recognised = list(data[CONF_DEVICE_CLASSES]) + list(data[CONF_KEYWORDS])
    shown = ", ".join(recognised[:3])
    if len(recognised) > 3:
        shown += f", +{len(recognised) - 3}"

    return f"{', '.join(names)} \u2190 {shown}"
