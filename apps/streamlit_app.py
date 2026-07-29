from __future__ import annotations

import os
from typing import Any, cast

import requests
import streamlit as st

DEFAULT_CHATBOT_API_URL = "http://localhost:8001"


def main() -> None:
    st.set_page_config(page_title="chatbot-incendie")
    st.title("chatbot-incendie")

    api_url = os.environ.get("CHATBOT_API_URL", DEFAULT_CHATBOT_API_URL).rstrip("/")
    messages = _messages()

    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                _render_citations(cast(list[dict[str, Any]], message.get("citations", [])))

    question = st.chat_input("Posez une question sur les incendies en Gironde ou dans les Landes")
    if question is None:
        return

    messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Recherche dans les sources indexées..."):
            response = _ask_api(api_url, question)
        st.markdown(response["answer"])
        citations = cast(list[dict[str, Any]], response.get("citations", []))
        _render_citations(citations)

    messages.append(
        {
            "role": "assistant",
            "content": response["answer"],
            "citations": citations,
        }
    )


def _messages() -> list[dict[str, Any]]:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    return cast(list[dict[str, Any]], st.session_state.messages)


def _ask_api(api_url: str, question: str) -> dict[str, Any]:
    try:
        response = requests.post(
            f"{api_url}/chat",
            json={"question": question, "top_k": 5},
            timeout=120,
        )
        response.raise_for_status()
        return cast(dict[str, Any], response.json())
    except requests.RequestException as error:
        return {
            "answer": f"Erreur lors de l'appel à l'API: {error}",
            "citations": [],
        }


def _render_citations(citations: list[dict[str, Any]]) -> None:
    if not citations:
        return
    with st.expander("Sources"):
        for index, citation in enumerate(citations, 1):
            title = citation.get("title") or citation.get("source_id") or "Source"
            url = citation.get("canonical_url") or citation.get("document_url") or ""
            score = citation.get("score")
            st.markdown(f"**[{index}] {title}**")
            if url:
                st.markdown(str(url))
            if score is not None:
                st.caption(f"Score: {score}")


if __name__ == "__main__":
    main()
