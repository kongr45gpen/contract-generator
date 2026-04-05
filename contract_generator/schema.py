from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ContractLoadError(RuntimeError):
    """Raised when a contract YAML file cannot be parsed or validated."""


class GenericParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    header: str | None = None
    footer: str | None = None


class ContractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template: str = Field(min_length=1)
    template_parameters: dict[str, Any] = Field(default_factory=dict)
    generic_parameters: GenericParameters = Field(default_factory=GenericParameters)


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


def load_contract_from_yaml(path: str | Path) -> ContractRequest:
    contract_path = Path(path)
    payload = _load_yaml(contract_path)

    try:
        return ContractRequest.model_validate(payload)
    except ValidationError as exc:
        raise ContractLoadError(str(exc)) from exc
