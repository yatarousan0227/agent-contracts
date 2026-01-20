"""Runtime helpers for the support assistant."""
from __future__ import annotations

from typing import Callable

from agent_contracts.runtime import AgentRuntime, RequestContext

from support_assistant.config import load_support_config
from support_assistant.data import INTENT_KEYWORDS, INTENT_PRIORITY, find_faq_topic
from support_assistant.graph import build_support_graph


def detect_intent(message: str) -> tuple[str, dict]:
    """Detect intent from message using keyword matching."""
    lowered = message.lower()
    for intent in INTENT_PRIORITY:
        for keyword in INTENT_KEYWORDS.get(intent, []):
            if keyword.lower() in lowered:
                if intent == "faq":
                    topic = find_faq_topic(message)
                    return "faq", {"topic": topic} if topic else {}
                return intent, {}
    return "fallback", {}


def build_request_context(
    message: str,
    session_id: str = "demo",
    use_llm: bool = False,
) -> RequestContext:
    """Create RequestContext with optional intent detection."""
    params: dict | None = None
    action: str | None = None
    if not use_llm:
        action, params = detect_intent(message)
    return RequestContext(
        session_id=session_id,
        action=action,
        params=params,
        message=message,
    )


def build_runtime(
    use_llm: bool = False,
    llm_provider: Callable[[], object] | None = None,
) -> AgentRuntime:
    """Build AgentRuntime with optional LLM support."""
    if use_llm and llm_provider is None:
        raise ValueError("llm_provider is required when use_llm is True.")
    load_support_config()
    graph = build_support_graph(llm_provider=llm_provider if use_llm else None)
    compiled = graph.compile()
    return AgentRuntime(compiled)
