"""Ollama 로컬 LLM 연결 및 모델 목록 조회."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class OllamaStatus:
    connected: bool
    message: str
    models: tuple[str, ...]


def get_ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")


def fetch_ollama_status(timeout: float = 3.0) -> OllamaStatus:
    """Ollama 서버 연결 여부와 설치된 모델 목록을 반환합니다."""
    base_url = get_ollama_base_url()
    url = f"{base_url}/api/tags"

    try:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        return OllamaStatus(
            connected=False,
            message=f"Ollama에 연결할 수 없습니다 ({base_url}): {exc.reason}",
            models=(),
        )
    except TimeoutError:
        return OllamaStatus(
            connected=False,
            message=f"Ollama 응답 시간 초과 ({base_url})",
            models=(),
        )
    except (json.JSONDecodeError, KeyError) as exc:
        return OllamaStatus(
            connected=False,
            message=f"Ollama 응답 파싱 실패: {exc}",
            models=(),
        )

    raw_models = payload.get("models", [])
    names: list[str] = []
    for item in raw_models:
        if isinstance(item, dict) and item.get("name"):
            names.append(str(item["name"]))

    names.sort()
    if not names:
        return OllamaStatus(
            connected=True,
            message="연결됨 — 설치된 모델이 없습니다. `ollama pull <model>` 로 모델을 받아주세요.",
            models=(),
        )

    return OllamaStatus(
        connected=True,
        message=f"연결됨 — 모델 {len(names)}개",
        models=tuple(names),
    )
