"""Streamlit 기반 LLM 코드 에이전트 - 엑셀 처리."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from agent.code_agent import CodeAgent
from agent.executor import CodeExecutor
from config import UPLOAD_DIR, get_llm_config
from services.excel_service import ExcelService
from services.ollama_service import fetch_ollama_status, get_ollama_base_url
from utils.session_state import (
    add_chat_entry,
    add_excel_file,
    get_excel_files,
    init_session_state,
    remove_excel_file,
)

load_dotenv()

st.set_page_config(
    page_title="LLM Agent Lab - Excel",
    page_icon="📊",
    layout="wide",
)

EXAMPLE_PROMPTS = [
    "업로드한 모든 엑셀 파일을 하나로 통합해줘.",
    "동일한 표 구조를 가진 파일들을 하나로 합치고, 숫자 항목은 평균값으로 계산해줘.",
    "첫 번째 파일에서 결측치가 있는 행을 제거해줘.",
    "모든 파일을 세로로 붙인 뒤 중복 행을 제거해줘.",
]


def refresh_ollama_status() -> None:
    st.session_state.ollama_status = fetch_ollama_status()


def get_ollama_status():
    if st.session_state.ollama_status is None:
        refresh_ollama_status()
    return st.session_state.ollama_status


def render_sidebar_ollama() -> str | None:
    """사이드바: Ollama 연결 상태 및 모델 선택."""
    st.sidebar.subheader("🦙 Ollama")
    status = get_ollama_status()

    if status.connected:
        st.sidebar.success(status.message, icon="🟢")
    else:
        st.sidebar.error(status.message, icon="🔴")

    st.sidebar.caption(f"서버: `{get_ollama_base_url()}`")

    if status.models:
        default_model = get_llm_config().model
        options = list(status.models)
        current = st.session_state.selected_ollama_model
        if current not in options:
            current = default_model if default_model in options else options[0]

        selected = st.sidebar.selectbox(
            "모델",
            options=options,
            index=options.index(current),
            help="Ollama에 설치된 로컬 모델 중 선택합니다.",
        )
        st.session_state.selected_ollama_model = selected
    else:
        st.sidebar.selectbox("모델", options=["(모델 없음)"], disabled=True)
        st.sidebar.caption("`ollama pull llama3.2` 등으로 모델을 설치하세요.")

    if st.sidebar.button("연결 새로고침", use_container_width=True):
        refresh_ollama_status()
        st.rerun()

    if not status.connected:
        st.sidebar.info(
            "Ollama 실행 후 `ollama serve`를 확인하세요. "
            "[설치 안내](https://ollama.com)"
        )
        return None

    return st.session_state.selected_ollama_model or None


def render_sidebar() -> str | None:
    selected_model = render_sidebar_ollama()
    st.sidebar.divider()

    st.sidebar.title("📁 엑셀 파일")
    st.sidebar.caption("xlsx / xls 파일을 업로드하고 관리합니다.")

    uploaded_files = st.sidebar.file_uploader(
        "파일 업로드",
        type=["xlsx", "xls"],
        accept_multiple_files=True,
        key="excel_uploader",
    )

    if uploaded_files:
        for uploaded in uploaded_files:
            if uploaded.name in get_excel_files():
                continue
            try:
                df = ExcelService.read_uploaded_file(uploaded, uploaded.name)
                add_excel_file(uploaded.name, df)
                st.sidebar.success(f"'{uploaded.name}' 업로드 완료")
            except Exception as exc:
                st.sidebar.error(f"'{uploaded.name}' 읽기 실패: {exc}")

    files = get_excel_files()
    st.sidebar.divider()

    if not files:
        st.sidebar.info("업로드된 파일이 없습니다.")
        return selected_model

    st.sidebar.subheader(f"파일 목록 ({len(files)}개)")
    for name, df in list(files.items()):
        with st.sidebar.expander(name, expanded=False):
            info = ExcelService.build_file_info(name, df)
            st.write(f"행: {info.rows} / 열: {info.columns}")
            st.dataframe(info.preview, use_container_width=True)
            if st.button("삭제", key=f"delete_{name}"):
                remove_excel_file(name)
                st.rerun()

    return selected_model


def get_runtime_llm_config():
    config = get_llm_config()
    selected = st.session_state.get("selected_ollama_model", "").strip()
    if selected:
        return replace(config, model=selected)
    return config


def run_agent(user_request: str) -> None:
    files = get_excel_files()
    if not files:
        st.error("먼저 엑셀 파일을 업로드해주세요.")
        return

    status = get_ollama_status()
    if not status.connected:
        st.error("Ollama에 연결되지 않았습니다. 서버를 실행한 뒤 새로고침해주세요.")
        return

    selected_model = st.session_state.get("selected_ollama_model", "").strip()
    if not selected_model:
        st.error("사용할 Ollama 모델을 선택해주세요. 모델이 없다면 `ollama pull`로 설치하세요.")
        return

    llm_config = get_runtime_llm_config()
    file_infos = [ExcelService.build_file_info(name, df) for name, df in files.items()]
    file_context = ExcelService.build_llm_context(file_infos)

    output_dir = UPLOAD_DIR / "results"
    executor = CodeExecutor(output_dir)
    agent = CodeAgent(llm_config, executor)

    with st.spinner(f"모델 `{llm_config.model}`로 코드 생성·실행 중..."):
        try:
            response = agent.run(user_request, files, file_context)
        except Exception as exc:
            st.error(f"에이전트 실행 실패: {exc}")
            return

    add_chat_entry(
        {
            "request": user_request,
            "code": response.generated_code,
            "success": response.execution.success,
            "error": response.execution.error,
            "stdout": response.execution.stdout,
            "saved_files": response.execution.saved_files,
            "result_preview": response.execution.result_preview,
            "result_df": response.execution.result,
            "model": response.llm_model,
        }
    )


def render_chat_history() -> None:
    for idx, entry in enumerate(st.session_state.chat_history):
        model_label = entry.get("model", "")
        st.markdown(f"**요청:** {entry['request']}")
        if model_label:
            st.caption(f"모델: `{model_label}`")

        with st.expander("생성된 코드", expanded=False):
            st.code(entry["code"], language="python")

        if entry["success"]:
            st.success("실행 성공")
            if entry.get("stdout"):
                st.text(entry["stdout"])

            if entry.get("result_df") is not None:
                st.subheader("결과 미리보기")
                st.dataframe(entry["result_df"], use_container_width=True)

                excel_bytes = ExcelService.to_excel_bytes(entry["result_df"])
                st.download_button(
                    "결과 엑셀 다운로드",
                    data=excel_bytes,
                    file_name=f"result_{idx + 1}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"download_result_{idx}",
                )

            for saved_path in entry.get("saved_files", []):
                path = Path(saved_path)
                if path.exists():
                    st.download_button(
                        f"저장 파일 다운로드: {path.name}",
                        data=path.read_bytes(),
                        file_name=path.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"download_saved_{idx}_{path.name}",
                    )
        else:
            st.error("실행 실패")
            st.code(entry.get("error", ""), language="text")

        st.divider()


def main() -> None:
    init_session_state()

    selected_model = render_sidebar()

    st.title("📊 LLM Agent Lab")
    st.markdown(
        "자연어 요청을 **Python 코드**로 변환해 엑셀 데이터를 처리하는 AI 에이전트입니다. "
        "로컬 **Ollama** 모델로 코드를 생성합니다."
    )

    st.subheader("💬 처리 요청")
    st.caption("업로드한 엑셀 파일에 대해 원하는 작업을 자연어로 입력하세요.")

    st.caption("예시 프롬프트 (클릭 시 입력란에 채워집니다)")
    cols = st.columns(len(EXAMPLE_PROMPTS))
    for idx, (col, example) in enumerate(zip(cols, EXAMPLE_PROMPTS)):
        if col.button(f"예시 {idx + 1}", key=f"example_{idx}", help=example):
            st.session_state.user_prompt = example
            st.rerun()

    st.text_area(
        "프롬프트",
        key="user_prompt",
        height=120,
        placeholder="예: 5개 엑셀 파일을 하나로 통합하고, 동일 표 항목의 숫자 값은 평균으로 계산해줘",
    )

    run_disabled = not selected_model
    if st.button("🚀 실행", type="primary", use_container_width=False, disabled=run_disabled):
        user_request = st.session_state.user_prompt.strip()
        if not user_request:
            st.warning("요청 내용을 입력해주세요.")
        else:
            run_agent(user_request)
            st.rerun()

    if st.session_state.chat_history:
        st.subheader("📋 실행 기록")
        render_chat_history()


if __name__ == "__main__":
    main()
