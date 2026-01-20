"""Human handoff node."""
from __future__ import annotations

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition


class HandoffNode(ModularNode):
    """Escalate to a human operator."""

    CONTRACT = NodeContract(
        name="handoff",
        description="Route to a human agent.",
        reads=["request"],
        writes=["response"],
        supervisor="support",
        is_terminal=True,
        trigger_conditions=[
            TriggerCondition(
                priority=60,
                when={"request.action": "handoff"},
                llm_hint="Escalate to a human agent.",
            )
        ],
    )

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(
            response={
                "response_type": "handoff",
                "response_message": "担当者におつなぎします。",
                "response_data": {"channel": "human_support"},
            }
        )
