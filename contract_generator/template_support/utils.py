from __future__ import annotations

from datetime import date

from contract_generator.template_support.types import InlineField


def format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def defaults_for_fields(contract: object, fields: tuple[InlineField, ...]) -> dict[str, str]:
    return {field.key: format_value(getattr(contract, field.key)) for field in fields}


def labels_for_fields(fields: tuple[InlineField, ...]) -> dict[str, str]:
    return {field.key: field.label for field in fields}


def widths_for_fields(fields: tuple[InlineField, ...]) -> dict[str, float]:
    return {field.key: field.width for field in fields}
