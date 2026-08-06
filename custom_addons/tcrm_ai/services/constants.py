# Part of TCRM AI. See LICENSE for details.
"""Approved providers/models and entitlement states for TCRM AI."""

GROQ_BASE_URL = 'https://api.groq.com/openai/v1'
# Default is the model currently permitted for the production Groq org.
# Larger models can be enabled in Settings when the org has access.
DEFAULT_GROQ_MODEL = 'openai/gpt-oss-20b'

# Browser must not submit arbitrary model names; only this server-side list.
APPROVED_GROQ_MODELS = [
    ('openai/gpt-oss-20b', 'openai/gpt-oss-20b'),
    ('openai/gpt-oss-120b', 'openai/gpt-oss-120b'),
    ('llama-3.3-70b-versatile', 'llama-3.3-70b-versatile'),
    ('qwen/qwen3-32b', 'qwen/qwen3-32b'),
]

APPROVED_PROVIDERS = [
    ('groq', 'Groq'),
]

SEARCH_PROVIDERS = [
    ('duckduckgo', 'DuckDuckGo'),
    ('brave', 'Brave Search'),
    ('serper', 'Serper'),
    ('none', 'Disabled'),
]

ENTITLEMENT_STATES = [
    ('unavailable', 'Kullanılamaz'),
    ('granted', 'Erişim Verildi'),
    ('config_required', 'Yapılandırma Gerekli'),
    ('active', 'Aktif'),
    ('suspended', 'Askıya Alındı'),
    ('quota_exceeded', 'Kota Aşıldı'),
    ('connection_error', 'Bağlantı Hatası'),
]

ENTITLEMENT_PARAM = 'tcrm_ai.entitlement_state'
SUSPENDED_PARAM = 'tcrm_ai.suspended'

# Default tenant limits (at or below typical Groq project caps).
DEFAULT_DAILY_REQUEST_LIMIT = 500
DEFAULT_DAILY_TOKEN_LIMIT = 500000
DEFAULT_MONTHLY_USAGE_LIMIT = 10000000
DEFAULT_RPM_LIMIT = 30
DEFAULT_MAX_TOOL_CALLS = 16
DEFAULT_MAX_OUTPUT_TOKENS = 4096
DEFAULT_REQUEST_TIMEOUT = 90
DEFAULT_RETENTION_DAYS = 90
DEFAULT_SEARCH_TIMEOUT = 12
DEFAULT_SEARCH_MAX_RESULTS = 5
DEFAULT_MONTHLY_SEARCH_QUOTA = 1000

# Soft cost estimate USD per 1M tokens (configurable display only).
GROQ_COST_PER_M_TOKENS = 0.10

# Typed frontend / API result statuses (never claim multi-provider capacity).
RESULT_STATUSES = (
    'success',
    'rate_limited',
    'invalid_configuration',
    'forbidden',
    'timeout',
    'provider_unavailable',
    'internal_error',
)

SAFE_ERROR_CODES = {
    'invalid_api_key': 'API anahtarı geçersiz',
    'model_denied': 'Model erişimine izin verilmiyor',
    'quota_exceeded': 'Groq isteği geçici olarak sınırlandı — lütfen kısa süre sonra tekrar deneyin.',
    'rate_limited': 'Çok hızlı istek gönderildi — lütfen kısa süre sonra tekrar deneyin.',
    'timeout': 'İstek zaman aşımına uğradı — lütfen tekrar deneyin.',
    'unreachable': 'Groq servisine ulaşılamadı',
    'provider_unavailable': 'AI sağlayıcısına şu an ulaşılamıyor.',
    'config_missing': 'Yapılandırma eksik',
    'invalid_configuration': 'AI yapılandırması geçersiz veya eksik.',
    'entitlement_denied': 'TCRM AI erişimi bu tenant için etkin değil',
    'suspended': 'TCRM AI askıya alındı',
    'permission_denied': 'Bu veri için yetkiniz yok',
    'forbidden': 'Bu işlem için yetkiniz yok.',
    'tool_denied': 'Bu araç kullanımına izin verilmiyor',
    'unknown': 'Beklenmeyen bir hata oluştu',
    'internal_error': 'Beklenmeyen bir hata oluştu',
}

# Map provider / internal codes → structured frontend status.
CODE_TO_STATUS = {
    'success': 'success',
    'quota_exceeded': 'rate_limited',
    'rate_limited': 'rate_limited',
    'invalid_api_key': 'invalid_configuration',
    'config_missing': 'invalid_configuration',
    'invalid_configuration': 'invalid_configuration',
    'model_denied': 'forbidden',
    'permission_denied': 'forbidden',
    'forbidden': 'forbidden',
    'entitlement_denied': 'forbidden',
    'suspended': 'forbidden',
    'tool_denied': 'forbidden',
    'timeout': 'timeout',
    'unreachable': 'provider_unavailable',
    'provider_unavailable': 'provider_unavailable',
    'unknown': 'internal_error',
    'internal_error': 'internal_error',
}


def format_retry_after(seconds: int | float | None, lang: str = 'tr') -> str:
    """Human-readable retry hint. Never shows '0 minutes'."""
    try:
        secs = int(round(float(seconds)))
    except (TypeError, ValueError):
        secs = 0
    if secs < 1:
        secs = 5
    if lang == 'en':
        if secs < 60:
            return 'Please try again in %s seconds.' % secs
        mins = max(1, secs // 60)
        return 'Please try again in %s minutes.' % mins
    if secs < 60:
        return '%s saniye sonra tekrar deneyin.' % secs
    mins = max(1, secs // 60)
    return '%s dakika sonra tekrar deneyin.' % mins


def rate_limit_user_message(seconds: int | float | None = None, lang: str = 'tr') -> str:
    hint = format_retry_after(seconds, lang=lang)
    if lang == 'en':
        return 'Groq temporarily rate-limited this request. %s' % hint
    return 'Groq isteği geçici olarak sınırlandı. %s' % hint
