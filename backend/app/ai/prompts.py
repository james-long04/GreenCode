"""Prompt construction for the two experimental conditions.

* ``ai_only``  – the model receives the original code and a generic request to
  optimise it. This is the control condition.
* ``greencode`` – the model additionally receives the structured findings from
  static analysis (rule, location, explanation, suggested change). This is the
  treatment condition.

Both prompts share the same system message, the same output contract and the
same constraints, so the *only* difference between conditions is the presence
of the findings. Keeping everything else identical is what makes the comparison
a fair test of H1–H3.
"""

from __future__ import annotations

from app.analysis.base import Finding

CONDITIONS = ("ai_only", "greencode")

SYSTEM_PYTHON = (
    "You are an expert Python performance engineer. You rewrite code so that it runs faster and uses "
    "fewer resources while producing exactly the same results for all inputs. You only use the Python "
    "standard library unless the original code already imports a third-party package. You never change "
    "the function's name, signature, return type or observable behaviour, and you never add printing, "
    "logging, file or network access."
)

SYSTEM_SQL = (
    "You are an expert PostgreSQL query engineer. You rewrite SQL queries so that they execute faster "
    "and do less work while returning exactly the same rows and columns (same column names, same order "
    "of columns, same row order when ORDER BY is present). You do not create indexes, change schema, or "
    "use features that are not available in PostgreSQL 16."
)

_OUTPUT_CONTRACT_PYTHON = (
    "Respond with the complete optimised Python module in a single ```python fenced code block and "
    "nothing else. The module must define the same top-level function(s) as the original, including "
    "`{entry_point}`."
)

_OUTPUT_CONTRACT_SQL = (
    "Respond with the complete optimised SQL statement in a single ```sql fenced code block and nothing "
    "else. Do not include explanations, comments or more than one statement."
)


def _schema_block(schema: str | None) -> str:
    if not schema:
        return ""
    return f"\nThe query runs against this PostgreSQL schema:\n```sql\n{schema.strip()}\n```\n"


def build_prompt(language: str, source: str, condition: str, findings: list[Finding] | None = None,
                 entry_point: str | None = None, schema: str | None = None) -> tuple[str, str]:
    """Return (system_message, prompt) for the given condition."""
    if condition not in CONDITIONS:
        raise ValueError(f"Unknown condition '{condition}'")
    language = language.lower()
    fence = "python" if language == "python" else "sql"
    system = SYSTEM_PYTHON if language == "python" else SYSTEM_SQL
    contract = (
        _OUTPUT_CONTRACT_PYTHON.format(entry_point=entry_point or "the original entry point")
        if language == "python" else _OUTPUT_CONTRACT_SQL
    )

    header = (
        "Optimise the following Python code for execution time, memory and energy efficiency."
        if language == "python"
        else "Optimise the following PostgreSQL query for execution time and resource usage."
    )

    guidance = ""
    if condition == "greencode":
        if findings:
            rendered = "\n".join(f.to_prompt_text(i + 1) for i, f in enumerate(findings))
            guidance = (
                "\nA static analyser has identified the following specific inefficiencies. Address each one "
                "directly. Do not make unrelated changes.\n\n"
                f"{rendered}\n"
            )
        else:
            guidance = (
                "\nA static analyser found no known inefficiency patterns in this code. If you cannot find a "
                "change that is clearly beneficial and behaviour-preserving, return the code unchanged.\n"
            )

    prompt = (
        f"{header}\n"
        f"{_schema_block(schema)}"
        f"\nOriginal:\n```{fence}\n{source.strip()}\n```\n"
        f"{guidance}\n"
        "Constraints:\n"
        "- Preserve exact behaviour and output for every possible input.\n"
        "- Do not change names, signatures or the set of returned columns.\n"
        "- Prefer simple, idiomatic changes with a clear algorithmic or I/O benefit.\n\n"
        f"{contract}"
    )
    return system, prompt
