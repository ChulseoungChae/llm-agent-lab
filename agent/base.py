"""에이전트 기본 인터페이스 - 기능 확장용."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class TaskContext:
    """에이전트 실행 컨텍스트."""

    user_request: str
    metadata: dict[str, Any]


class BaseAgent(ABC):
    """새 기능 에이전트는 이 클래스를 상속해 구현합니다."""

    name: str = "base"
    description: str = ""

    @abstractmethod
    def run(self, context: TaskContext) -> Any:
        raise NotImplementedError
