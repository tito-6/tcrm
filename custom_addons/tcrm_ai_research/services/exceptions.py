# Part of TCRM AI Research. See LICENSE for details.
"""Typed exceptions for the RAGFlow research provider layer."""


class RagflowError(Exception):
    """Base error for provider failures (safe to map to user messages)."""

    def __init__(self, message: str, *, category: str = 'provider_error', status_code: int | None = None):
        super().__init__(message)
        self.category = category
        self.status_code = status_code


class RagflowAuthError(RagflowError):
    def __init__(self, message: str = 'RAGFlow authentication failed'):
        super().__init__(message, category='auth', status_code=401)


class RagflowTimeoutError(RagflowError):
    def __init__(self, message: str = 'RAGFlow request timed out'):
        super().__init__(message, category='timeout', status_code=504)


class RagflowRateLimitError(RagflowError):
    def __init__(self, message: str = 'RAGFlow rate limit exceeded'):
        super().__init__(message, category='rate_limit', status_code=429)


class RagflowValidationError(RagflowError):
    def __init__(self, message: str = 'Invalid RAGFlow response'):
        super().__init__(message, category='validation', status_code=502)


class RagflowNotFoundError(RagflowError):
    def __init__(self, message: str = 'RAGFlow resource not found'):
        super().__init__(message, category='not_found', status_code=404)
