# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
from __future__ import annotations

from typing import Dict, Type

from .base import BaseMarketConnector, ConnectorError

_REGISTRY: Dict[str, Type[BaseMarketConnector]] = {}


def register(cls: Type[BaseMarketConnector]):
    _REGISTRY[cls.source_type] = cls
    return cls


def get_connector(env, source) -> BaseMarketConnector:
    cls = _REGISTRY.get(source.source_type)
    if not cls:
        raise ConnectorError("Unknown source type: %s" % source.source_type)
    return cls(env, source)


def list_connector_types():
    return sorted(_REGISTRY.keys())
