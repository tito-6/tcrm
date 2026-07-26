# Part of TCRM AI. See LICENSE for details.

"""
Manages selection of the best available key across all providers.
Round-robin within provider; fallover to next provider when all keys unavailable.
"""

from .unified_types import AllProvidersExhaustedError, KeySlot


class KeyPool:
    """Per-provider key pool with round-robin and cooldown-aware selection."""

    ROUND_ROBIN_PARAM_PREFIX = 'tcrm_ai.round_robin.'

    def __init__(self, env):
        self.env = env

    def _get_providers_ordered(self):
        return self.env['tcrm.ai.provider'].sudo().search([
            ('active', '=', True),
            ('key_ids', '!=', False),
        ], order='priority asc, id asc')

    def _reset_cooldowns_for_keys(self, keys):
        if keys:
            keys.reset_if_cooldown_expired()

    def _get_round_robin_index(self, provider_code):
        param = self.ROUND_ROBIN_PARAM_PREFIX + provider_code
        value = self.env['ir.config_parameter'].sudo().get_param(param, '0')
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _set_round_robin_index(self, provider_code, index):
        param = self.ROUND_ROBIN_PARAM_PREFIX + provider_code
        self.env['ir.config_parameter'].sudo().set_param(param, str(index))

    def get_next_key(self):
        """
        Returns the best available key slot right now.
        Raises AllProvidersExhaustedError if none available.
        """
        providers = self._get_providers_ordered()
        if not providers:
            raise AllProvidersExhaustedError(None)

        # Reset cooldowns for all keys
        all_keys = self.env['tcrm.ai.key'].sudo().search([
            ('provider_id', 'in', providers.ids),
            ('active', '=', True),
        ])
        self._reset_cooldowns_for_keys(all_keys)

        for provider in providers:
            keys = provider.key_ids.filtered(lambda k: k.active and k.is_available())
            if not keys:
                continue
            # Round-robin within this provider's active keys
            keys = keys.sorted(key=lambda k: (k.sequence, k.id))
            idx = self._get_round_robin_index(provider.provider_code)
            idx = idx % len(keys) if keys else 0
            key = keys[idx]
            # Advance for next time
            self._set_round_robin_index(provider.provider_code, (idx + 1) % len(keys))
            return KeySlot(
                id=key.id,
                api_key=key.api_key,
                provider_code=provider.provider_code,
                default_model=provider.default_model,
                key_label=key.name,
                provider_id=provider.id,
            )

        next_time = self.get_next_available_time()
        raise AllProvidersExhaustedError(next_time)

    def report_rate_limited(self, key_slot):
        """Called when a 429 is received for this key."""
        key = self.env['tcrm.ai.key'].sudo().browse(key_slot.id)
        if key.exists():
            key.mark_rate_limited()

    def report_exhausted(self, key_slot):
        """Called when daily quota is confirmed exceeded."""
        key = self.env['tcrm.ai.key'].sudo().browse(key_slot.id)
        if key.exists():
            key.mark_exhausted()

    def report_error(self, key_slot, error_message):
        """Called on 500/503 or connection error."""
        key = self.env['tcrm.ai.key'].sudo().browse(key_slot.id)
        if key.exists():
            key.mark_error(error_message)

    def report_success(self, key_slot, tokens_used=0):
        """Called after successful response."""
        key = self.env['tcrm.ai.key'].sudo().browse(key_slot.id)
        if key.exists():
            key.mark_success(tokens_used)

    def get_health_report(self):
        """Returns full status of every provider and key for Settings UI."""
        providers = self._get_providers_ordered()
        result = []
        for provider in providers:
            result.append({
                'id': provider.id,
                'name': provider.name,
                'provider_code': provider.provider_code,
                'priority': provider.priority,
                'health_status': provider.health_status,
                'active_key_count': provider.active_key_count,
                'total_key_count': len(provider.key_ids),
                'keys': [
                    {
                        'id': k.id,
                        'name': k.name,
                        'status': k.status,
                        'cooldown_until': k.cooldown_until,
                        'rpm_count': k.rpm_count,
                        'rpd_count': k.rpd_count,
                    }
                    for k in provider.key_ids
                ],
            })
        return result

    def get_next_available_time(self):
        """
        If all keys are down, returns the earliest datetime
        when any key will recover from cooldown.
        """
        keys = self.env['tcrm.ai.key'].sudo().search([
            ('active', '=', True),
            ('cooldown_until', '!=', False),
        ])
        if not keys:
            return None
        return min(k.cooldown_until for k in keys)
