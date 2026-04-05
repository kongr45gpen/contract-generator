from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from typing import Callable

from pydantic import BaseModel, ValidationError

from contract_generator.schema import ContractLoadError
from contract_generator.template_support.types import Clause, InlineField


@dataclass(frozen=True)
class TemplateDefinition:
    name: str
    description: str
    parameters_model: type[BaseModel]
    build_clauses: Callable[[BaseModel], tuple[Clause, ...]]
    notes_line: Callable[[BaseModel], str | None]
    inline_editable_fields: tuple[InlineField, ...]


def _discover_templates() -> dict[str, TemplateDefinition]:
    discovered: dict[str, TemplateDefinition] = {}
    templates_package = importlib.import_module("contract_generator.templates")

    for module_info in pkgutil.iter_modules(templates_package.__path__):
        module = importlib.import_module(f"contract_generator.templates.{module_info.name}")
        required_attributes = (
            "TEMPLATE_NAME",
            "TEMPLATE_DESCRIPTION",
            "PARAMETERS_MODEL",
            "INLINE_EDITABLE_FIELDS",
            "build_clauses",
            "notes_line",
        )
        if not all(hasattr(module, attribute) for attribute in required_attributes):
            continue

        name = getattr(module, "TEMPLATE_NAME")
        discovered[name] = TemplateDefinition(
            name=name,
            description=getattr(module, "TEMPLATE_DESCRIPTION"),
            parameters_model=getattr(module, "PARAMETERS_MODEL"),
            build_clauses=getattr(module, "build_clauses"),
            notes_line=getattr(module, "notes_line"),
            inline_editable_fields=getattr(module, "INLINE_EDITABLE_FIELDS"),
        )

    return discovered


_TEMPLATES: dict[str, TemplateDefinition] = _discover_templates()


def list_templates() -> tuple[TemplateDefinition, ...]:
    return tuple(_TEMPLATES[key] for key in sorted(_TEMPLATES))


def get_template_definition(name: str) -> TemplateDefinition:
    definition = _TEMPLATES.get(name)
    if definition is None:
        available = ", ".join(sorted(_TEMPLATES))
        raise ContractLoadError(f"Unsupported template '{name}'. Available templates: {available}")
    return definition


def validate_template_parameters(definition: TemplateDefinition, payload: dict[str, object]) -> BaseModel:
    try:
        return definition.parameters_model.model_validate(payload)
    except ValidationError as exc:
        raise ContractLoadError(str(exc)) from exc
