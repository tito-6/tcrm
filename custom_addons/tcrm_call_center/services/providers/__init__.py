# -*- coding: utf-8 -*-
from .base import CallProviderBase
from .twilio_provider import TwilioCallProvider


def get_provider(env, config):
    """Factory for the configured voice provider (outbound now; inbound later)."""
    if not config or not config.exists():
        raise ValueError('Santral yapılandırılmamış')
    provider = (config.provider or '').lower()
    if provider == 'twilio':
        return TwilioCallProvider(env, config)
    raise ValueError('Unsupported Santral provider: %s' % provider)
