# Part of TCRM AI Research. See LICENSE for details.
"""Abstract research provider interface (RAGFlow-agnostic)."""

from __future__ import annotations

from typing import Any, Iterator


class BaseResearchProvider:
    """Adapter contract so RAGFlow can be replaced without rewriting UI/models."""

    def create_dataset(self, name: str, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def list_datasets(self, name: str | None = None, **kwargs: Any) -> list[dict[str, Any]]:
        raise NotImplementedError

    def create_chat(self, name: str, dataset_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def create_session(self, chat_id: str, name: str = 'New session', **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def upload_document(
        self,
        dataset_id: str,
        filename: str,
        content: bytes,
        content_type: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def parse_documents(self, dataset_id: str, document_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def get_document_status(self, dataset_id: str, document_id: str, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def delete_document(self, dataset_id: str, document_ids: list[str], **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def ask(
        self,
        question: str,
        *,
        chat_id: str | None = None,
        session_id: str | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any] | Iterator[dict[str, Any]]:
        raise NotImplementedError
