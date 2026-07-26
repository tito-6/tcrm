# -*- coding: utf-8 -*-
import importlib.util
from pathlib import Path


def migrate(cr, version):
    from tcrm import SUPERUSER_ID, api

    env = api.Environment(cr, SUPERUSER_ID, {})
    hook_path = Path(__file__).resolve().parents[2] / "hooks.py"
    spec = importlib.util.spec_from_file_location("tcrm_org_hooks", hook_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.post_init_hook(env)
