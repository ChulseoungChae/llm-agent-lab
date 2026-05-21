"""Streamlit 세션 상태 초기화."""

from __future__ import annotations

import streamlit as st
import pandas as pd


def init_session_state() -> None:
    defaults = {
        "excel_files": {},
        "chat_history": [],
        "result_files": {},
        "selected_ollama_model": "",
        "ollama_status": None,
        "user_prompt": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_excel_files() -> dict[str, pd.DataFrame]:
    return st.session_state.excel_files


def add_excel_file(name: str, dataframe: pd.DataFrame) -> None:
    st.session_state.excel_files[name] = dataframe


def remove_excel_file(name: str) -> None:
    st.session_state.excel_files.pop(name, None)


def add_chat_entry(entry: dict) -> None:
    st.session_state.chat_history.append(entry)


def add_result_file(name: str, path: str) -> None:
    st.session_state.result_files[name] = path
