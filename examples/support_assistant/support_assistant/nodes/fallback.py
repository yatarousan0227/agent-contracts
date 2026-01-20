"""Fallback node."""
from __future__ import annotations

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition


class FallbackNode(ModularNode):
    """Handle unsupported requests."""

    CONTRACT = NodeContract(
        name="fallback",
        description="Fallback response for unsupported intents.",
        reads=["request"],
        writes=["response"],
        supervisor="support",
        is_terminal=True,
        trigger_conditions=[
            TriggerCondition(
                priority=1,
                llm_hint="Fallback response when intent is unclear.",
            )
        ],
    )

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(
            response={
                "response_type": "fallback",
                "response_message": "内容を確認できませんでした。詳しく教えてください。",
                "response_data": {"next": "clarify"},
            }
        )
