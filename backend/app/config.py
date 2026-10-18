"""Application settings.

All configuration is read from environment variables (or a ``.env`` file) so that
experiments can be reproduced by recording the environment alongside results.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GREENCODE_", env_file=".env", extra="ignore")

    # --- persistence -----------------------------------------------------
    database_url: str = Field(
        default="postgresql+psycopg://greencode:greencode@localhost:5432/greencode",
        description="SQLAlchemy URL for the evidence store.",
    )
    # Separate connection for the controlled SQL benchmark dataset. Defaults to the
    # same database (schema ``bench``) so a single PostgreSQL instance is enough.
    benchmark_database_url: str = Field(
        default="postgresql://greencode:greencode@localhost:5432/greencode",
        description="libpq URL used by the SQL verifier/benchmark runner.",
    )
    benchmark_schema: str = "bench"

    # --- AI --------------------------------------------------------------
    llm_provider: str = Field(default="ollama", description="ollama | mock")
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:7b"
    ollama_timeout_seconds: float = 300.0
    llm_temperature: float = 0.0
    llm_seed: int = 42

    # --- verification / sandbox ------------------------------------------
    sandbox_timeout_seconds: float = 20.0
    sandbox_memory_limit_mb: int = 512
    sandbox_cpu_seconds: int = 30
    python_executable: str | None = None

    # --- benchmarking ----------------------------------------------------
    benchmark_warmup_runs: int = 3
    benchmark_repetitions: int = 15
    benchmark_timeout_seconds: float = 120.0
    sql_statement_timeout_ms: int = 30_000

    # --- energy / carbon -------------------------------------------------
    energy_method: str = Field(
        default="auto",
        description="auto | rapl | pcm | lhm | codecarbon | estimate. 'auto' picks the best available.",
    )
    # Path to Intel PCM's pcm.exe (Windows). Unset means search PATH.
    pcm_path: str | None = None
    # LibreHardwareMonitor web server (Windows). Enable it in LHM: Options > Remote Web Server > Run.
    lhm_url: str = "http://localhost:8085/data.json"
    carbon_factor_region: str = "IE"
    estimate_cpu_tdp_watts: float = 65.0
    estimate_memory_watts_per_gb: float = 0.3725  # Green Algorithms (Lannelongue et al., 2021)
    estimate_pue: float = 1.0

    # --- api -------------------------------------------------------------
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    benchmark_suite_dir: str = "../benchmarks"
    # Shared secret for /api/admin/*. Always required: when unset, a random token
    # is generated at startup and printed in the server log (see app.main).
    admin_token: str | None = None


# Settings that the admin panel may change at runtime. They apply to this process
# only (a restart reverts to the environment), and every optimisation records the
# values it actually ran with, so reproducibility is not affected.
RUNTIME_ADJUSTABLE: frozenset[str] = frozenset({
    "llm_provider", "ollama_model", "ollama_base_url", "llm_temperature", "llm_seed",
    "benchmark_warmup_runs", "benchmark_repetitions", "benchmark_timeout_seconds",
    "energy_method", "pcm_path", "lhm_url", "carbon_factor_region", "estimate_cpu_tdp_watts", "estimate_pue",
    "sandbox_timeout_seconds", "sandbox_memory_limit_mb",
})

_overrides: dict[str, object] = {}


@lru_cache
def _env_settings() -> Settings:
    return Settings()


def get_settings() -> Settings:
    """Effective settings: environment values with any runtime overrides applied."""
    base = _env_settings()
    if not _overrides:
        return base
    return base.model_copy(update=dict(_overrides))


def runtime_overrides() -> dict[str, object]:
    return dict(_overrides)


def set_runtime_overrides(values: dict[str, object]) -> Settings:
    """Validate and apply overrides for adjustable keys. Returns the effective settings."""
    unknown = set(values) - RUNTIME_ADJUSTABLE
    if unknown:
        raise ValueError(f"not adjustable at runtime: {', '.join(sorted(unknown))}")
    candidate = _env_settings().model_copy(update={**_overrides, **values})
    # Re-validate through pydantic so a bad type or value is rejected before it is applied.
    validated = Settings.model_validate(candidate.model_dump())
    for key in values:
        _overrides[key] = getattr(validated, key)
    return get_settings()


def clear_runtime_overrides() -> Settings:
    _overrides.clear()
    return get_settings()


_generated_token: str | None = None


def effective_admin_token() -> str:
    """The admin token in force: the configured one, or a per-process random one."""
    global _generated_token
    configured = get_settings().admin_token
    if configured:
        return configured
    if _generated_token is None:
        import secrets

        _generated_token = secrets.token_urlsafe(24)
    return _generated_token


def admin_token_is_generated() -> bool:
    return not get_settings().admin_token


# Scripts that change os.environ call get_settings.cache_clear(); keep that working.
get_settings.cache_clear = _env_settings.cache_clear  # type: ignore[attr-defined]
