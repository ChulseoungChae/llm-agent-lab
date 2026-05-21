"""생성된 Python 코드 안전 실행."""

from __future__ import annotations

import builtins
import importlib
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

_FILES_ONLY_MSG = (
    "pd.read_excel() 및 디스크 파일 경로 접근은 사용할 수 없습니다. "
    "업로드된 데이터는 이미 DataFrame으로 로드되어 있습니다. "
    '예: df = files["파일명.xlsx"]'
)

_EXCEPTION_BUILTINS = {
    name: getattr(builtins, name)
    for name in (
        "BaseException",
        "Exception",
        "ArithmeticError",
        "AssertionError",
        "AttributeError",
        "FileNotFoundError",
        "IndexError",
        "KeyError",
        "LookupError",
        "NameError",
        "OSError",
        "RuntimeError",
        "StopIteration",
        "TypeError",
        "ValueError",
        "ZeroDivisionError",
    )
}

# 생성 코드에서 import 허용할 모듈 (루트 이름 기준)
ALLOWED_IMPORT_ROOTS = frozenset({"pandas", "numpy", "pathlib"})


def _safe_import(
    name: str,
    globals: dict[str, Any] | None = None,
    locals: dict[str, Any] | None = None,
    fromlist: tuple[str, ...] = (),
    level: int = 0,
) -> Any:
    """허용 목록에 있는 모듈만 import합니다."""
    root = name.split(".")[0]
    if root not in ALLOWED_IMPORT_ROOTS:
        allowed = ", ".join(sorted(ALLOWED_IMPORT_ROOTS))
        raise ImportError(
            f"모듈 '{name}'은(는) import할 수 없습니다. 허용 모듈: {allowed}"
        )
    return importlib.__import__(name, globals, locals, fromlist, level)


class _SandboxPandas:
    """read_excel 등 디스크 접근 API를 차단한 pandas 프록시."""

    __slots__ = ()

    @staticmethod
    def read_excel(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(_FILES_ONLY_MSG)

    def __getattr__(self, name: str) -> Any:
        return getattr(pd, name)


_SANDBOX_PD = _SandboxPandas()


@dataclass
class CodeExecutionResult:
    success: bool
    result: pd.DataFrame | None = None
    saved_files: list[str] = field(default_factory=list)
    stdout: str = ""
    error: str = ""
    result_preview: str = ""


class CodeExecutor:
    """제한된 네임스페이스에서 pandas 코드를 실행합니다."""

    ALLOWED_BUILTINS: dict[str, Any] = {
        "__import__": _safe_import,
        "abs": abs,
        "all": all,
        "any": any,
        "bool": bool,
        "dict": dict,
        "enumerate": enumerate,
        "float": float,
        "int": int,
        "len": len,
        "list": list,
        "max": max,
        "min": min,
        "print": print,
        "range": range,
        "round": round,
        "set": set,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "zip": zip,
        "True": True,
        "False": False,
        "None": None,
        "isinstance": isinstance,
        "hasattr": hasattr,
        "getattr": getattr,
        "repr": repr,
        **_EXCEPTION_BUILTINS,
    }

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def execute(
        self,
        code: str,
        files: dict[str, pd.DataFrame],
    ) -> CodeExecutionResult:
        namespace: dict[str, Any] = {
            "__builtins__": dict(self.ALLOWED_BUILTINS),
            "files": files,
            "pd": _SANDBOX_PD,
            "np": np,
            "OUTPUT_DIR": self.output_dir,
            "saved_files": [],
            "result": None,
        }

        stdout_lines: list[str] = []

        def capture_print(*args: Any, **kwargs: Any) -> None:
            stdout_lines.append(" ".join(str(arg) for arg in args))

        namespace["__builtins__"]["print"] = capture_print

        try:
            exec(code, namespace)
        except Exception:
            return CodeExecutionResult(
                success=False,
                error=traceback.format_exc(),
                stdout="\n".join(stdout_lines),
            )

        result = namespace.get("result")
        saved_files = namespace.get("saved_files", [])
        if not isinstance(saved_files, list):
            saved_files = []

        saved_paths = [str(path) for path in saved_files if path]

        if result is not None and not isinstance(result, pd.DataFrame):
            return CodeExecutionResult(
                success=False,
                error=f"`result`는 DataFrame이어야 합니다. 현재 타입: {type(result).__name__}",
                stdout="\n".join(stdout_lines),
            )

        preview = ""
        if isinstance(result, pd.DataFrame):
            preview = result.head(20).to_string()

        return CodeExecutionResult(
            success=True,
            result=result,
            saved_files=saved_paths,
            stdout="\n".join(stdout_lines),
            result_preview=preview,
        )
