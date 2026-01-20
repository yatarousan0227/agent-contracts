"""FAQ response node."""
from __future__ import annotations

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition

from support_assistant.data import FAQ_ENTRIES, find_faq_topic


class FaqNode(ModularNode):
    """Answer common FAQ questions."""

    CONTRACT = NodeContract(
        name="faq_answer",
        description="Answer frequently asked questions.",
        reads=["request"],
        writes=["response"],
        supervisor="support",
        is_terminal=True,
        trigger_conditions=[
            TriggerCondition(
                priority=40,
                when={"request.action": "faq"},
                llm_hint="Answer FAQs about password reset, billing, or troubleshooting.",
            )
        ],
    )

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        request = inputs.get_slice("request")
        params = request.get("params") or {}
        message = (request.get("message") or "").strip()
        topic = params.get("topic") or find_faq_topic(message)
        entry = FAQ_ENTRIES.get(topic or "", {})
        answer = entry.get("answer") if entry else None
        if not answer:
            answer = "該当するFAQが見つかりませんでした。"
        return NodeOutputs(
            response={
                "response_type": "faq_answered",
                "response_message": answer,
                "response_data": {"topic": topic, "source": "faq"},
            }
        )
