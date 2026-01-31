"""Minimal hierarchical supervisor example with a subgraph call."""
from __future__ import annotations

import asyncio
from typing import Any

from agent_contracts import (
    GenericSupervisor,
    ModularNode,
    NodeContract,
    NodeInputs,
    NodeOutputs,
    NodeRegistry,
    SubgraphContract,
    SubgraphDefinition,
    TriggerCondition,
    build_graph_from_registry,
)


class TrendNode(ModularNode):
    """Return a simple fashion trend response."""

    CONTRACT = NodeContract(
        name="trend_node",
        description="Return current fashion trend",
        reads=["request"],
        writes=["response"],
        supervisor="fashion",
        is_terminal=True,
        trigger_conditions=[TriggerCondition(priority=1)],
    )

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        request = inputs.get_slice("request")
        message = request.get("message") or "(no message)"
        return NodeOutputs(
            response={
                "response_type": "fashion_trend",
                "response_message": f"Trend for '{message}': clean silhouettes + bold textures.",
            }
        )


def _route_domain(state: dict[str, Any]) -> str | None:
    request = state.get("request", {})
    if not isinstance(request, dict):
        return "done"
    if request.get("action") != "fashion":
        return "done"

    internal = state.get("_internal", {})
    if not isinstance(internal, dict):
        return "call_subgraph::fashion"

    visited = internal.get("visited_subgraphs", {})
    if isinstance(visited, dict) and visited.get("fashion", 0) > 0:
        return "done"
    return "call_subgraph::fashion"


def build_registry() -> NodeRegistry:
    registry = NodeRegistry()
    registry.register(TrendNode)

    contract = SubgraphContract(
        subgraph_id="fashion",
        description="Fashion trend subgraph",
        reads=["request"],
        writes=["response"],
        entrypoint="fashion",
    )
    definition = SubgraphDefinition(
        subgraph_id="fashion",
        supervisors=["fashion"],
        nodes=["trend_node"],
    )
    registry.register_subgraph(contract, definition)
    return registry


def build_graph() -> Any:
    registry = build_registry()

    def supervisor_factory(name: str, llm: Any) -> GenericSupervisor:
        if name == "domain":
            return GenericSupervisor(
                supervisor_name=name,
                llm=None,
                registry=registry,
                explicit_routing_handler=_route_domain,
            )
        return GenericSupervisor(
            supervisor_name=name,
            llm=None,
            registry=registry,
        )

    graph = build_graph_from_registry(
        registry=registry,
        supervisors=["domain"],
        llm_provider=lambda: None,
        supervisor_factory=supervisor_factory,
        enable_subgraphs=True,
    )
    graph.set_entry_point("domain_supervisor")
    return graph.compile()


async def main() -> None:
    compiled = build_graph()
    result = await compiled.ainvoke(
        {
            "request": {
                "action": "fashion",
                "message": "Fall collection",
            },
            "response": {},
            "_internal": {},
        }
    )

    print("Response:")
    print(result.get("response", {}))
    print("Decision trace:")
    print(result.get("_internal", {}).get("decision_trace", []))


if __name__ == "__main__":
    asyncio.run(main())
