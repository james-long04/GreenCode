"""Core types shared by the Python and SQL analysers.

A *rule* is a deterministic detector for one named inefficiency pattern. Every
rule produces zero or more ``Finding`` objects. Findings are the "structured
finding" that distinguishes the GreenCode condition from the AI-only condition:
they are passed to the language model as explicit guidance.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

ANALYSER_VERSION = "0.1.0"


@dataclass
class Finding:
    rule_id: str
    title: str
    explanation: str
    suggestion: str
    severity: str = "medium"  # low | medium | high
    category: str = "performance"
    line: int | None = None
    column: int | None = None
    end_line: int | None = None
    snippet: str | None = None
    confidence: float = 0.8
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_prompt_text(self, index: int) -> str:
        """Render the finding for inclusion in an LLM prompt."""
        where = f" (line {self.line})" if self.line else ""
        parts = [
            f"{index}. [{self.rule_id}] {self.title}{where}",
            f"   Why it is inefficient: {self.explanation}",
            f"   Suggested change: {self.suggestion}",
        ]
        if self.snippet:
            parts.append(f"   Code: {self.snippet.strip()}")
        return "\n".join(parts)


@dataclass
class RuleInfo:
    rule_id: str
    name: str
    language: str
    category: str
    severity: str
    description: str


@dataclass
class AnalysisResult:
    language: str
    findings: list[Finding]
    duration_ms: float
    analyser_version: str = ANALYSER_VERSION
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "findings": [f.to_dict() for f in self.findings],
            "duration_ms": self.duration_ms,
            "analyser_version": self.analyser_version,
            "error": self.error,
            "metadata": self.metadata,
        }
