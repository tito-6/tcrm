# Part of TCRM AI. See LICENSE for details.

from .base_adapter import BaseAdapter
from .gemini_adapter import GeminiAdapter
from .openai_adapter import OpenAIAdapter
from .anthropic_adapter import AnthropicAdapter
from .groq_adapter import GroqAdapter
from .mistral_adapter import MistralAdapter
from .ollama_adapter import OllamaAdapter

ADAPTERS = {
    'gemini': GeminiAdapter(),
    'openai': OpenAIAdapter(),
    'anthropic': AnthropicAdapter(),
    'groq': GroqAdapter(),
    'mistral': MistralAdapter(),
    'ollama': OllamaAdapter(),
}


def get_adapter(provider_code):
    return ADAPTERS.get(provider_code)
