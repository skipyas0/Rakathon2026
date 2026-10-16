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
    # OpenAI-compatible chat endpoint (Azure APIM, EU data zone); key sent as `api-key` header
    azure_api_key: str | None = None
    llm_base_url: str = "https://apim-rakathon-q7146n.azure-api.net/openai/v1"
    llm_model: str = "gpt-6-luna-dz-eu"
    # TrueType fonts embedded in PDFs (need Czech glyphs); None = first found in pdf.FONT_CANDIDATES
    pdf_font: Path | None = None
    pdf_font_bold: Path | None = None
    # Shared password (HTTP basic auth, any username) for the deployed app; unset = no login
    app_password: str | None = None


settings = Settings()
