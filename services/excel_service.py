"""엑셀 파일 업로드·관리 서비스."""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import BinaryIO

import pandas as pd


@dataclass
class ExcelFileInfo:
    name: str
    rows: int
    columns: int
    column_names: list[str]
    dtypes: dict[str, str]
    preview: pd.DataFrame


class ExcelService:
    """업로드된 엑셀 파일을 세션 단위로 관리합니다."""

    @staticmethod
    def read_uploaded_file(uploaded_file: BinaryIO, filename: str) -> pd.DataFrame:
        data = uploaded_file.read()
        buffer = io.BytesIO(data)
        return pd.read_excel(buffer, engine="openpyxl")

    @staticmethod
    def build_file_info(name: str, dataframe: pd.DataFrame) -> ExcelFileInfo:
        preview = dataframe.head(5).copy()
        return ExcelFileInfo(
            name=name,
            rows=len(dataframe),
            columns=len(dataframe.columns),
            column_names=[str(col) for col in dataframe.columns],
            dtypes={str(col): str(dtype) for col, dtype in dataframe.dtypes.items()},
            preview=preview,
        )

    @staticmethod
    def build_llm_context(file_infos: list[ExcelFileInfo]) -> str:
        if not file_infos:
            return "업로드된 파일이 없습니다."

        sections: list[str] = []
        for info in file_infos:
            preview_text = info.preview.to_string(index=False)
            dtypes_text = ", ".join(f"{k}: {v}" for k, v in info.dtypes.items())
            sections.append(
                "\n".join(
                    [
                        f"### {info.name}",
                        f"- 행: {info.rows}, 열: {info.columns}",
                        f"- 컬럼: {', '.join(info.column_names)}",
                        f"- dtype: {dtypes_text}",
                        "- 미리보기:",
                        preview_text,
                    ]
                )
            )
        return "\n\n".join(sections)

    @staticmethod
    def to_excel_bytes(dataframe: pd.DataFrame) -> bytes:
        buffer = io.BytesIO()
        dataframe.to_excel(buffer, index=False, engine="openpyxl")
        return buffer.getvalue()
