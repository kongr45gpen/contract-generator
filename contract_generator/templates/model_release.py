from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html import escape

from jinja2 import Template

from contract_generator.schema import ModelReleaseContract


@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    span: int = 1


FIELD_SPECS: list[FieldSpec] = [
    FieldSpec("subject_name", "Release Subject"),
    FieldSpec("company_name", "Releasee / Company"),
    FieldSpec("project_name", "Project Name"),
    FieldSpec("effective_date", "Effective Date"),
    FieldSpec("location", "Location"),
    FieldSpec("email", "Email"),
    FieldSpec("consideration", "Consideration"),
    FieldSpec("governing_law", "Governing Law"),
    FieldSpec("usage_scope", "Usage Scope", span=2),
]

MODEL_RELEASE_BODY = Template(
    """
    <b>Release Grant.</b> I, {{ subject_name }}, grant {{ company_name }} permission to use my name, likeness, voice, image, and any related materials in connection with {{ project_name }}.
    <br/><br/>
    <b>Scope.</b> The permitted use includes {{ usage_scope }}.
    <br/><br/>
    <b>Terms.</b> This release is effective on {{ effective_date }} in {{ location }}. Consideration: {{ consideration }}. Governing law: {{ governing_law }}.
    {% if notes %}
    <br/><br/>
    <b>Notes.</b> {{ notes }}
    {% endif %}
    """.strip()
)


def _format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, date):
        return value.isoformat()
    return escape(str(value))


def render_model_release_body(contract: ModelReleaseContract) -> str:
    context = {field: _format_value(value) for field, value in contract.model_dump().items()}
    return MODEL_RELEASE_BODY.render(**context)
