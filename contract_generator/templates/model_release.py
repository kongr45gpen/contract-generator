from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from contract_generator.template_support.types import Clause, InlineField


class Parameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_title: str = Field(default="Model Release Form", min_length=1)
    subject_name: str = Field(min_length=1)
    project_name: str = Field(min_length=1)
    effective_date: date
    location: str = Field(min_length=1)
    company_name: str = Field(default="Production Company", min_length=1)
    email: str | None = None
    usage_scope: str = Field(default="All media, worldwide, in perpetuity", min_length=1)
    consideration: str = Field(default="Included in project fee", min_length=1)
    governing_law: str = Field(default="California", min_length=1)
    notes: str | None = None


TEMPLATE_NAME = "model_release"
TEMPLATE_DESCRIPTION = "Model Release Form"
PARAMETERS_MODEL = Parameters

EDITABLE_SUBJECT_NAME = InlineField("subject_name", "Release Subject", 116)
EDITABLE_PROJECT_NAME = InlineField("project_name", "Project Name", 122)
EDITABLE_EFFECTIVE_DATE = InlineField("effective_date", "Effective Date", 48)
EDITABLE_LOCATION = InlineField("location", "Location", 108)
EDITABLE_EMAIL = InlineField("email", "Email", 136)


INLINE_EDITABLE_FIELDS: tuple[InlineField, ...] = (
    EDITABLE_SUBJECT_NAME,
    EDITABLE_PROJECT_NAME,
    EDITABLE_EFFECTIVE_DATE,
    EDITABLE_LOCATION,
    EDITABLE_EMAIL,
)


def build_clauses(contract: Parameters) -> tuple[Clause, ...]:
    return (
        Clause(
            "Release Grant",
            (
                "I, ",
                EDITABLE_SUBJECT_NAME,
                f", grant {contract.company_name} permission to use my name, likeness, voice, image, and related materials in connection with ",
                EDITABLE_PROJECT_NAME,
                ".",
            ),
        ),
        Clause(
            "Scope",
            (
                "Permitted use includes ",
                f"{contract.usage_scope}",
                ".",
            ),
        ),
        Clause(
            "Terms",
            (
                "This release is effective on ",
                EDITABLE_EFFECTIVE_DATE,
                " in ",
                EDITABLE_LOCATION,
                f". Consideration: {contract.consideration}. Governing law: {contract.governing_law}.",
            ),
        ),
        Clause(
            "Contact",
            (
                "The subject can be reached at ",
                EDITABLE_EMAIL,
                ".",
            ),
        ),
    )


def notes_line(contract: Parameters) -> str | None:
    if not contract.notes:
        return None
    return f"Notes: {contract.notes}"
