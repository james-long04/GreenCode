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
        description="auto | rapl | codecarbon | estimate. 'auto' picks the best available.",
    )
    carbon_factor_region: str = "IE"
    estimate_cpu_tdp_watts: float = 65.0
    estimate_memory_watts_per_gb: float = 0.3725  # Green Algorithms (Lannelongue et al., 2021)
    estimate_pue: float = 1.0

    # --- api -------------------------------------------------------------
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    benchmark_suite_dir: str = "../benchmarks"


@lru_cache
def get_settings() -> Settings:
    return Settings()
