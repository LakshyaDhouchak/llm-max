"""Re-exports the canonical FakeOllamaAdapter from llm_max.testing.fakes.

Kept as a thin shim (rather than deleting) so existing test files can keep
their `from tests.fakes.fake_ollama_adapter import FakeOllamaAdapter`
imports unchanged. The real implementation lives in the installable
package (llm_max/testing/fakes/) specifically so other packages in this
monorepo — agentd, and later webui if it ever needs Python test doubles —
can import the exact same fake via a normal package import
(`from llm_max.testing.fakes import FakeOllamaAdapter`) instead of each
maintaining (and silently drifting from) their own copy.
"""

from llm_max.testing.fakes.fake_ollama_adapter import FakeOllamaAdapter

__all__ = ["FakeOllamaAdapter"]