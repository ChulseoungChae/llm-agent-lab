"""요청 기반 Python 코드 생성 에이전트."""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd
from openai import OpenAI

from agent.executor import CodeExecutionResult, CodeExecutor
from agent.prompts import SYSTEM_PROMPT, build_user_prompt
from config import LLMConfig


@dataclass
class AgentResponse:
    user_request: str
    generated_code: str
    execution: CodeExecutionResult
    llm_model: str


class CodeAgent:
    """자연어 요청을 Python 코드로 변환하고 실행합니다."""

    def __init__(self, llm_config: LLMConfig, executor: CodeExecutor) -> None:
        self.llm_config = llm_config
        self.executor = executor
        self.client = OpenAI(
            api_key="ollama",
            base_url=llm_config.base_url,
        )

    def run(
        self,
        user_request: str,
        files: dict[str, pd.DataFrame],
        file_context: str,
    ) -> AgentResponse:
        file_names = list(files.keys())
        generated_code = self._generate_code(user_request, file_context, file_names)
        execution = self.executor.execute(generated_code, files)
        return AgentResponse(
            user_request=user_request,
            generated_code=generated_code,
            execution=execution,
            llm_model=self.llm_config.model,
        )

    def _generate_code(
        self,
        user_request: str,
        file_context: str,
        file_names: list[str],
    ) -> str:
        user_prompt = build_user_prompt(user_request, file_context, file_names)
        response = self.client.chat.completions.create(
            model=self.llm_config.model,
            temperature=self.llm_config.temperature,
            max_tokens=self.llm_config.max_tokens,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content or ""
        return self._extract_python_code(content)

    @staticmethod
    def _extract_python_code(content: str) -> str:
        pattern = r"```(?:python)?\s*(.*?)```"
        matches = re.findall(pattern, content, flags=re.DOTALL | re.IGNORECASE)
        if matches:
            return matches[0].strip()
        return content.strip()
