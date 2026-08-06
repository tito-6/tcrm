from . import models
from . import controllers
from . import services


def post_init_hook(env):
    """Migrate legacy Gemini selections and seed entitlement for master DB."""
    from .models.tcrm_ai_config import DEPRECATED_GEMINI_TO_CURRENT
    from .services import entitlement as entitlement_svc
    from .services.constants import DEFAULT_GROQ_MODEL, GROQ_BASE_URL

    for old_model, new_model in DEPRECATED_GEMINI_TO_CURRENT.items():
        env['tcrm.ai.config'].search([('gemini_model', '=', old_model)]).write(
            {'gemini_model': new_model}
        )
        if env.get('tcrm.ai.provider'):
            env['tcrm.ai.provider'].search([
                ('provider_code', '=', 'gemini'),
                ('default_model', '=', old_model),
            ]).write({'default_model': new_model})

    # Prefer Groq defaults on existing configs missing new fields
    configs = env['tcrm.ai.config'].search([])
    for config in configs:
        vals = {}
        if not config.provider:
            vals['provider'] = 'groq'
        if not config.base_url:
            vals['base_url'] = GROQ_BASE_URL
        if not config.model:
            vals['model'] = DEFAULT_GROQ_MODEL
        if vals:
            config.write(vals)

    # Master DB gets local entitlement active by default (own key still required).
    if entitlement_svc.is_master_database(env):
        state = entitlement_svc.get_entitlement_state(env)
        if state == 'unavailable':
            entitlement_svc.set_entitlement_state(env, 'config_required')

    # Encrypt legacy plaintext provider keys if present
    try:
        from .services.crypto import encrypt_secret, ENC_PREFIX
        for key in env['tcrm.ai.key'].sudo().search([]):
            raw = key.api_key or ''
            if raw and not str(raw).startswith(ENC_PREFIX):
                key.write({'api_key': encrypt_secret(env, raw)})
    except Exception:
        pass
