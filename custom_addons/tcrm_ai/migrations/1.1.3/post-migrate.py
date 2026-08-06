# Part of TCRM AI. See LICENSE for details.
"""Dedupe AI configs and sync a valid Groq key from the provider pool."""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from tcrm import SUPERUSER_ID, api, modules
    from tcrm.addons.tcrm_ai.services.crypto import encrypt_secret, normalize_api_key
    from tcrm.addons.tcrm_ai.services import entitlement as entitlement_svc

    env = api.Environment(cr, SUPERUSER_ID, {})
    Config = env['tcrm.ai.config'].sudo()
    companies = Config.search([]).mapped('company_id')
    for company in companies:
        configs = Config.search([('company_id', '=', company.id)], order='id asc')
        if len(configs) <= 1:
            keep = configs
        else:
            ranked = configs.sorted(
                key=lambda c: (
                    1 if c.ai_enabled else 0,
                    1 if c.api_key_encrypted else 0,
                    1 if c.last_connection_status == 'ok' else 0,
                    -c.id,
                ),
                reverse=True,
            )
            keep = ranked[:1]
            (configs - keep).unlink()
            _logger.info('TCRM AI 1.1.3: removed duplicate configs for company %s', company.id)

        if not keep:
            continue
        config = keep
        key = normalize_api_key(
            config._get_plaintext_api_key() if hasattr(config, '_get_plaintext_api_key') else ''
        )
        if key.startswith('gsk_'):
            continue
        if 'tcrm.ai.key' not in env:
            continue
        slots = env['tcrm.ai.key'].sudo().search([
            ('provider_id.provider_code', '=', 'groq'),
            ('active', '=', True),
        ], order='sequence asc, id asc')
        provider_key = ''
        for slot in slots:
            candidate = normalize_api_key(slot.api_key)
            if candidate.startswith('gsk_'):
                provider_key = candidate
                break
        if not provider_key:
            continue
        config.write({
            'api_key_encrypted': encrypt_secret(env, provider_key),
            'provider': 'groq',
            'last_connection_status': 'unknown',
            'last_safe_error': False,
        })
        _logger.info('TCRM AI 1.1.3: synced Groq provider key into config id=%s', config.id)

    # Ensure unique(company_id) exists after cleanup.
    cr.execute("""
        SELECT 1 FROM pg_constraint
        WHERE conname = 'tcrm_ai_config_company_uniq'
    """)
    if not cr.fetchone():
        try:
            cr.execute("""
                ALTER TABLE tcrm_ai_config
                ADD CONSTRAINT tcrm_ai_config_company_uniq UNIQUE (company_id)
            """)
        except Exception as exc:
            _logger.warning('TCRM AI 1.1.3: could not add unique constraint: %s', exc)

    # Refresh modules registry helper unused; silence linters.
    _ = modules
