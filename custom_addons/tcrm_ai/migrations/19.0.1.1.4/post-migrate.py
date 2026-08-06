# Part of TCRM AI. See LICENSE for details.
"""Enable fuller AI access + stronger default Groq model."""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    from tcrm import SUPERUSER_ID, api
    from tcrm.addons.tcrm_ai.services.constants import DEFAULT_GROQ_MODEL

    env = api.Environment(cr, SUPERUSER_ID, {})
    Config = env['tcrm.ai.config'].sudo()
    for config in Config.search([]):
        vals = {
            'allow_crm_data': True,
            'allow_sales_data': True,
            'allow_property_data': True,
            'allow_payment_data': True,
            'allow_reports': True,
            'allow_internet_research': True,
            'max_tool_calls': max(config.max_tool_calls or 0, 16),
            'max_output_tokens': max(config.max_output_tokens or 0, 4096),
            'request_timeout': max(config.request_timeout or 0, 90),
            'daily_request_limit': max(config.daily_request_limit or 0, 500),
            'daily_token_limit': max(config.daily_token_limit or 0, 500000),
            'rpm_limit': max(config.rpm_limit or 0, 30),
        }
        # Keep a working Groq model; do not force models the org may block.
        if not config.model:
            vals['model'] = DEFAULT_GROQ_MODEL
        elif config.model not in (
            'openai/gpt-oss-20b', 'openai/gpt-oss-120b',
            'llama-3.3-70b-versatile', 'qwen/qwen3-32b',
        ):
            vals['model'] = DEFAULT_GROQ_MODEL
        config.write(vals)
        _logger.info('TCRM AI 1.1.4: expanded access on config id=%s model=%s', config.id, config.model)
