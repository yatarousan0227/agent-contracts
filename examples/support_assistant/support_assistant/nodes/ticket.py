"""Ticket creation node."""
from __future__ import annotations

from uuid import uuid4

from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition


class CreateTicketNode(ModularNode):
    """Create a support ticket."""

    CONTRACT = NodeContract(
        name="create_ticket",
        description="Create a support ticket for complex issues.",
        reads=["request"],
        writes=["ticket", "response"],
        supervisor="support",
        is_terminal=True,
        trigger_conditions=[
            TriggerCondition(
                priority=50,
                when={"request.action": "create_ticket"},
                llm_hint="Create a support ticket for the user.",
            )
        ],
    )

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        request = inputs.get_slice("request")
        params = request.get("params") or {}
        title = params.get("title") or request.get("message") or "Support request"
        ticket_id = f"TCK-{uuid4().hex[:6].upper()}"
        return NodeOutputs(
            ticket={"id": ticket_id, "title": title, "status": "open"},
            response={
                "response_type": "ticket_created",
                "response_message": "サポートチケットを作成しました。",
                "response_data": {"ticket_id": ticket_id, "title": title},
            },
        )
