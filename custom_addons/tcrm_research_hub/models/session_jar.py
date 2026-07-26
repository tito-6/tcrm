# -*- coding: utf-8 -*-
"""Per-TCRM-user Google cookie jar for Research Hub proxy + NotebookLM sync."""
from __future__ import annotations

import logging
import os
import pickle
import tempfile

_logger = logging.getLogger(__name__)

try:
    import requests as _requests
    HAS_REQUESTS = True
except ImportError:
    _requests = None
    HAS_REQUESTS = False

_JAR_CACHE: dict[int, object] = {}


def jar_path(uid: int) -> str:
    root = os.path.join(tempfile.gettempdir(), "tcrm_research_hub_jars")
    os.makedirs(root, exist_ok=True)
    return os.path.join(root, f"uid_{uid}.pkl")


def load_session(uid: int):
    if not HAS_REQUESTS:
        return None
    if uid in _JAR_CACHE:
        return _JAR_CACHE[uid]
    sess = _requests.Session()
    path = jar_path(uid)
    if os.path.isfile(path):
        try:
            with open(path, "rb") as fh:
                data = pickle.load(fh)
            if hasattr(data, "items") and not isinstance(data, dict):
                sess.cookies = data
            elif isinstance(data, dict) and "jar" in data:
                sess.cookies = data["jar"]
            elif isinstance(data, dict) and "cookies" in data:
                sess.cookies = _requests.utils.cookiejar_from_dict(data["cookies"])
        except Exception as exc:
            _logger.warning("Research Hub: could not load cookie jar for uid=%s: %s", uid, exc)
    _JAR_CACHE[uid] = sess
    return sess


def save_session(uid: int, sess) -> None:
    try:
        path = jar_path(uid)
        with open(path, "wb") as fh:
            pickle.dump({"jar": sess.cookies}, fh)
    except Exception as exc:
        _logger.warning("Research Hub: could not save cookie jar for uid=%s: %s", uid, exc)


def clear_session(uid: int) -> None:
    _JAR_CACHE.pop(uid, None)
    path = jar_path(uid)
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass
