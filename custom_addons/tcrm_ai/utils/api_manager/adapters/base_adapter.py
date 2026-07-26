# Part of TCRM AI. See LICENSE for details.

from abc import ABC, abstractmethod


class BaseAdapter(ABC):
    """Abstract base for provider-specific REST adapters."""

    @abstractmethod
    def build_request(
        self,
        messages,
        tools=None,
        max_tokens=1000,
        temperature=0.7,
        api_key=None,
        model=None,
    ):
        """Build the provider-specific HTTP request body/params."""

    @abstractmethod
    def call(self, request):
        """Execute the HTTP call. Return raw requests.Response."""

    @abstractmethod
    def parse_response(self, raw_response):
        """Convert provider response to UnifiedResponse."""

    @abstractmethod
    def is_rate_limited(self, raw_response):
        """True if HTTP 429 or rate limit message in body."""

    @abstractmethod
    def is_quota_exhausted(self, raw_response):
        """True if daily/monthly quota is fully used up."""

    @abstractmethod
    def is_server_error(self, raw_response):
        """True if 500, 502, 503, 504."""

    @abstractmethod
    def is_success(self, raw_response):
        """True if 200 with valid content."""
