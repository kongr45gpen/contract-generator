from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from contract_generator.template_support.types import Clause, InlineField


class Parameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_title: str = Field(default="Video Release Form", min_length=1)

    party_name: str | None = None
    party_email: str | None = None

    company_name: str = Field(min_length=1)
    extra_parties: list[str] = Field(default_factory=list)
    project_name: str = Field(min_length=1)
    effective_date: date
    dates: str = Field(min_length=1)
    location: str = Field(min_length=1)

    notes: str | None = None


TEMPLATE_NAME = "video_release"
TEMPLATE_DESCRIPTION = "Video Release Form"
PARAMETERS_MODEL = Parameters

EDITABLE_PARTY_NAME = InlineField("party_name", "Releasor", 116)

# EDITABLE_EMAIL = InlineEditableField("email", "Email", 136)


INLINE_EDITABLE_FIELDS: tuple[InlineField, ...] = (
    EDITABLE_PARTY_NAME,
)


def _publish_rights_parties_text(contract: Parameters) -> str:
    extra = [party.strip() for party in contract.extra_parties if party.strip()]
    if not extra:
        return ""
    return f"I agree that the following additional authorized parties have rights to publish and reproduce materials including my name, voice and likeness under this agreement within the scope described above: {', '.join(extra)}."


def build_clauses(contract: Parameters) -> tuple[Clause, ...]:
    clauses: list[Clause] = [
        Clause(
            "Release Grant",
            (
                "I, ",
                EDITABLE_PARTY_NAME,
                f"hereby grant {contract.company_name} (\"Releasee\") the right and permission to publish, reproduce, or otherwise use my name, voice, and likeness as captured on audio, written, photographic, or video recordings during the date(s) of {contract.dates}, which took place in {contract.location}, for the scope of the \"{contract.project_name}\" project.",
            ),
        ),
        Clause(
            "",
            (
                "I understand that my image may be edited, copied, exhibited, published, or distributed, and I waive the right to inspect or approve the finished product wherein my likeness appears.",
            ),
        ),
        Clause(
            "",
            (
                "I agree that I have been compensated for this use of my likeness or have otherwise agreed to this release without being compensated. Additionally, I waive any right to royalties or other compensation arising or related to the use of my image or recording. I understand and agree that the recorded materials will be the sole property of Releasee and will not be returned to me. I also understand that these materials may be used for any lawful purpose and in any manner, form, or format whatsoever now or hereinafter created, including, but not limited to, the Internet, advertisements, e-mails, social media, and television.",
            ),
        ),
        Clause(
            "",
            (
                "There is no time limit on the validity of this release nor is there any geographic limitation on where these materials may be distributed.",
            ),
        ),
        Clause(
            "",
            (
                "I hereby hold Releasee harmless from all liability, petitions, and causes of action which I, my heirs, representatives, executors, administrators, or any other persons may make while acting on my behalf or on behalf of my estate.",
            ),
        ),
        Clause(
            "",
            (
                "By signing this release, I acknowledge that I am 18 years old or older, and that I have completely read and fully understand the above release and agree to be bound thereby.",
            ),
        ),
    ]

    additional_parties_clause = _publish_rights_parties_text(contract)
    if additional_parties_clause:
        clauses.append(
            Clause(
                "Additional Parties",
                (additional_parties_clause,),
            ),
        )

    return tuple(clauses)


def notes_line(contract: Parameters) -> str | None:
    if not contract.notes:
        return None
    return f"Notes: {contract.notes}"
