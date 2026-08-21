"""Fixed prompt set used for benchmarking.

Deliberately not user-supplied: results from different prompts aren't
comparable (a one-word answer and a long generation have very different
tokens/sec profiles), so `llm-max tune` always benchmarks against this same
fixed set — short/medium/long — regardless of what the user later runs.
"""

from __future__ import annotations

BENCHMARK_PROMPTS: list[str] = [
    # short — mostly measures latency/overhead, not sustained throughput
    "Say hello in one short sentence.",
    # medium — typical chat-length response
    "Explain what a linked list is and why it's useful, in a short paragraph.",
    # long — measures sustained generation throughput
    (
        "Write a detailed explanation of how neural networks learn through "
        "backpropagation, covering the forward pass, loss computation, "
        "gradient calculation, and weight updates."
    ),
]