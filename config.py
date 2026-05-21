"""애플리케이션 설정."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from services.ollama_service import get_ollama_base_url


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


@dataclass(frozen=True)
class LLMConfig:
    model: str
    base_url: str
    temperature: float
    max_tokens: int


def get_llm_config() -> LLMConfig:
    base = get_ollama_base_url()
    return LLMConfig(
        model=os.getenv("OLLAMA_MODEL", "llama3.2"),
        base_url=f"{base}/v1",
        temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.1")),
        max_tokens=int(os.getenv("OLLAMA_MAX_TOKENS", "4096")),
    )
