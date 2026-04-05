from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ContractLoadError(RuntimeError):
    """Raised when a contract YAML file cannot be parsed or validated."""


class ModelReleaseContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template: Literal["model_release"] = "model_release"
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


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - surfaced in CLI path handling
        raise ContractLoadError(f"Unable to read contract file: {path}") from exc

    try:
        loaded = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ContractLoadError(f"Invalid YAML in contract file: {path}") from exc

    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ContractLoadError("Contract YAML must define a mapping at the top level.")
    return loaded


def load_contract_from_yaml(path: str | Path) -> ModelReleaseContract:
    contract_path = Path(path)
    payload = _load_yaml(contract_path)

    template = payload.get("template", "model_release")
    if template != "model_release":
        raise ContractLoadError(f"Unsupported template '{template}'. Only 'model_release' is available.")

    try:
        return ModelReleaseContract.model_validate(payload)
    except ValidationError as exc:
        raise ContractLoadError(str(exc)) from exc
