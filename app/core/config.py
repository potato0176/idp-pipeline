"""Application configuration using Pydantic Settings."""

from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Application ---
    app_name: str = "IDP-Pipeline"
    app_env: str = "development"
    debug: bool = True

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000

    # --- VLM (Gemma 3 27b via Ollama OpenAI-compatible API) ---
    vlm_api_base: str = "http://localhost:11434/v1"
    vlm_model: str = "gemma3:27b"
    vlm_timeout: int = 120

    # --- OCR ---
    ocr_languages: str = "ch_tra,en"
    ocr_gpu: bool = True

    # --- Vector Database ---
    chroma_persist_dir: str = "./data/chroma_db"
    embedding_model: str = "all-MiniLM-L6-v2"

    # --- Chunking ---
    chunk_size: int = 512
    chunk_overlap: int = 50

    # --- File Storage ---
    upload_dir: str = "./data/uploads"
    output_dir: str = "./data/outputs"
    max_file_size_mb: int = 50

    @property
    def ocr_language_list(self) -> list[str]:
        return [lang.strip() for lang in self.ocr_languages.split(",")]

    def ensure_directories(self) -> None:
        """Create necessary data directories if they don't exist."""
        for dir_path in [self.upload_dir, self.output_dir, self.chroma_persist_dir]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
