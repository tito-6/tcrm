# -*- coding: utf-8 -*-
"""Authorized market-data source adapters.

Scraping, CAPTCHA bypass, and unauthorized Sahibinden execution are refused.
"""
from .registry import get_connector, list_connector_types
from . import csv_connector  # noqa: F401
from . import xlsx_connector  # noqa: F401
from . import json_connector  # noqa: F401
from . import demo_connector  # noqa: F401
from . import sahibinden  # noqa: F401
