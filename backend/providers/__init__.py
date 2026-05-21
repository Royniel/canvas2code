from .gemini import GeminiProvider
from .groq import GroqProvider
from .openrouter import OpenRouterProvider

PROVIDERS = {
    "gemini": GeminiProvider(),
    "groq": GroqProvider(),
    "openrouter": OpenRouterProvider(),
}

__all__ = ["PROVIDERS", "GeminiProvider", "GroqProvider", "OpenRouterProvider"]
