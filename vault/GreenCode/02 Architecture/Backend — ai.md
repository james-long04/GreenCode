---
title: Backend — ai
created: 2026-10-22
project: GreenCode
tags: [architecture, backend, ai]
---

# `ai/` — talking to the model

## `provider.py`
`LLMProvider` (abstract: `generate(prompt, system) -> GenerationResult`, `model_name`, `health()`).
- `OllamaProvider` — POST `/api/generate` on `http://localhost:11434`, `temperature`, `seed`, `stream: false`; returns text, token counts, wall time.
- `MockProvider` — canned responses (default: echoes the original inside a fence); lets the pipeline and tests run without a GPU.
- `build_provider(settings)` picks by `GREENCODE_LLM_PROVIDER` (`ollama | mock`).

## `prompts.py` — **the file that keeps the experiment valid**
`build_prompt(language, source, condition, findings, entry_point, schema) -> (system, prompt)`.
Shared by both conditions: system message (`SYSTEM_PYTHON` / `SYSTEM_SQL`), header, schema block (SQL), constraints, output contract (single fenced block, same entry point / same columns).
The **only** branch on `condition`:
- `greencode` with findings → "A static analyser has identified the following specific inefficiencies. Address each one directly. Do not make unrelated changes." + numbered findings.
- `greencode` with no findings → "…found no known inefficiency patterns… If you cannot find a change that is clearly beneficial and behaviour-preserving, return the code unchanged."
- `ai_only` → nothing.

> Edit shared parts only, and run pytest: `tests/test_ai.py` asserts the two prompts are identical apart from the findings block. See [[01 Project/Ground rules]].

## `parsing.py`
`extract_code(response, language)` finds the fenced block with a matching tag (`python|py`, `sql|postgresql`…), falls back to an untagged fence, cleans trailing semicolons/prose, raises `CandidateParseError` → optimisation `failed` with `parse_error` (counts against H1).
