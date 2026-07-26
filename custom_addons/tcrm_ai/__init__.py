from . import models
from . import controllers


def post_init_hook(cr, registry):
    """One-time: migrate deprecated Gemini model selections and clear placeholder key."""
    from tcrm import api
    from .models.tcrm_ai_config import DEPRECATED_GEMINI_TO_CURRENT
    env = api.Environment(cr, api.SUPERUSER_ID, {})
    for old_model, new_model in DEPRECATED_GEMINI_TO_CURRENT.items():
        env["tcrm.ai.config"].search([("gemini_model", "=", old_model)]).write(
            {"gemini_model": new_model}
        )
        if env.get("tcrm.ai.provider"):
            env["tcrm.ai.provider"].search([
                ("provider_code", "=", "gemini"),
                ("default_model", "=", old_model),
            ]).write({"default_model": new_model})
    env["tcrm.ai.config"].search([
        ("gemini_api_key", "=", "AIzaSyDJsDRb_jjhIaQIGThhDQQWPTEp5LooFF0")
    ]).write({"gemini_api_key": ""})
