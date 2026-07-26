# -*- coding: utf-8 -*-
"""Provider interface — outbound first; inbound hooks reserved for later."""
from __future__ import annotations

from abc import ABC, abstractmethod


class CallProviderBase(ABC):
    name = 'base'

    def __init__(self, env, config):
        self.env = env
        self.config = config

    @abstractmethod
    def test_connection(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def create_access_token(self, *, identity: str, ttl_seconds: int = 300) -> dict:
        raise NotImplementedError

    @abstractmethod
    def build_outgoing_twiml(self, *, to_number: str, from_number: str, call_record, status_callback: str, recording_callback: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def validate_webhook_signature(self, url: str, params: dict, signature: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def fetch_recording_bytes(self, recording_sid: str) -> tuple[bytes, str]:
        raise NotImplementedError

    # Reserved for inbound milestone
    def build_inbound_twiml(self, **kwargs):  # pragma: no cover - future
        raise NotImplementedError('Inbound routing is not enabled in this milestone.')
