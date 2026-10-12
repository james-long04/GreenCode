"""Extract the candidate code from a model response."""

from __future__ import annotations

import re

_FENCE_RE = re.compile(r"```([a-zA-Z0-9_+-]*)[ \t]*\n(.*?)```", re.DOTALL)


class CandidateParseError(ValueError):
    pass


def extract_code(response: str, language: str) -> str:
    """Return the code from the first fenced block that matches the language.

    Falls back to the first fenced block of any language, then to the raw text if
    it looks like code. Raises ``CandidateParseError`` when nothing usable is found.
    """
    language = language.lower()
    blocks = _FENCE_RE.findall(response)
    preferred = [body for lang, body in blocks if lang.lower() in _aliases(language)]
    if preferred:
        return _clean(preferred[0], language)
    if blocks:
        return _clean(blocks[0][1], language)
    text = response.strip()
    if not text:
        raise CandidateParseError("Model returned an empty response.")
    if language == "python" and ("def " in text or "import " in text):
        return _clean(text, language)
    if language == "sql" and re.match(r"(?is)^\s*(select|with|insert|update|delete)\b", text):
        return _clean(text, language)
    raise CandidateParseError("No code block found in model response.")


def _aliases(language: str) -> set[str]:
    return {"python", "py", "python3"} if language == "python" else {"sql", "postgresql", "postgres", "pgsql"}


def _clean(code: str, language: str) -> str:
    code = code.strip("\n")
    if language == "sql":
        # Keep only the first statement; strip a trailing semicolon for EXPLAIN wrapping.
        stripped = code.strip()
        if ";" in stripped:
            first = stripped.split(";")[0].strip()
            if first:
                stripped = first
        return stripped
    return code
