from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InlineField:
    key: str
    label: str
    width: float


@dataclass(frozen=True)
class Clause:
    heading: str
    segments: tuple[str | InlineField, ...]
