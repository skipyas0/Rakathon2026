from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Values come from env vars or ../.env (see .env.example at repo root).
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    fhir_base_url: str = "http://localhost:8080/fhir"
    fhir_user: str | None = None  # Basic auth, needed for IRIS (HAPI needs none)
    fhir_password: str | None = None
    # The organisers' dataset (git-ignored): pacienti/<ID>_bundle.json, guidelines/, studie/
    dataset_dir: Path = Path(__file__).parents[3] / "Dataset"


settings = Settings()
