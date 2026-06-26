"""LLM pricing per provider/model.

Costs are in USD per 1,000,000 tokens. Free-tier providers (e.g. Groq's
free Llama models) keep estimated_cost = 0 — but input/output tokens are
still tracked for usage analytics. Update entries when upstream providers
adjust rates; values below are illustrative as of 2026.
"""
from decimal import Decimal


# provider -> model -> {input, output} USD per 1M tokens
PRICING: dict[str, dict[str, dict[str, Decimal]]] = {
    "gemini": {
        "gemini-2.5-flash": {
            "input": Decimal("0.075"),
            "output": Decimal("0.30"),
        },
    },
    "groq": {
        # Free tier — tokens tracked, cost = 0.
        "llama-3.2-90b-vision-preview": {
            "input": Decimal("0"),
            "output": Decimal("0"),
        },
        "llama-3.2-11b-vision-preview": {
            "input": Decimal("0"),
            "output": Decimal("0"),
        },
    },
    "openrouter": {
        # Indicative; OpenRouter pricing varies by upstream model.
        "qwen/qwen-2-vl-72b-instruct": {
            "input": Decimal("0.4"),
            "output": Decimal("0.4"),
        },
    },
    "judge": {
        # Mirrors Gemini Flash since the judge uses it.
        "gemini-2.5-flash": {
            "input": Decimal("0.075"),
            "output": Decimal("0.30"),
        },
    },
}


def calculate_cost(
    provider: str, model: str, input_tokens: int, output_tokens: int
) -> Decimal:
    rates = PRICING.get(provider, {}).get(model)
    if rates is None:
        # Unknown model — track tokens at $0 cost rather than refusing the log.
        return Decimal("0")
    return (
        (Decimal(input_tokens) * rates["input"])
        + (Decimal(output_tokens) * rates["output"])
    ) / Decimal("1000000")
