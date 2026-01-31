"""Tests for CallSubgraph nodes and hierarchical budgets."""

import pytest

from agent_contracts import (
    ModularNode,
    NodeContract,
    NodeInputs,
    NodeOutputs,
    TriggerCondition,
    NodeRegistry,
    SubgraphContract,
    SubgraphDefinition,
    build_graph_from_registry,
    GenericSupervisor,
)


class ChildNode(ModularNode):
    """Terminal node inside a subgraph."""
    CONTRACT = NodeContract(
        name="child_node",
        description="Child subgraph node",
        reads=["request"],
        writes=["response"],
        supervisor="child",
        is_terminal=True,
        trigger_conditions=[TriggerCondition(priority=1)],
    )

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(
            response={
                "response_type": "child_done",
                "response_data": {"child": True},
            }
        )


class ParentSupervisor:
    """Minimal supervisor that calls a subgraph once, then stops."""
    def __init__(self, target: str) -> None:
        self.target = target

    async def run(self, state: dict, config=None) -> dict:
        internal = state.get("_internal", {})
        response = state.get("response", {})
        response_type = None
        if isinstance(response, dict):
            response_type = response.get("response_type")
        if response_type in {"child_done", "terminal"}:
            decision = "done"
        else:
            decision = self.target
        return {"_internal": {**(internal if isinstance(internal, dict) else {}), "decision": decision}}


@pytest.fixture
def registry():
    reg = NodeRegistry()
    reg.register(ChildNode)

    contract = SubgraphContract(
        subgraph_id="child_graph",
        description="Test child subgraph",
        reads=["request"],
        writes=["response"],
        entrypoint="child",
    )
    definition = SubgraphDefinition(
        subgraph_id="child_graph",
        supervisors=["child"],
        nodes=["child_node"],
    )
    reg.register_subgraph(contract, definition)
    return reg


def _build_subgraph_graph(registry, *, allowlists=None):
    def supervisor_factory(name: str, llm):
        if name == "main":
            return ParentSupervisor("call_subgraph::child_graph")
        return GenericSupervisor(
            supervisor_name=name,
            llm=None,
            registry=registry,
        )

    graph = build_graph_from_registry(
        registry=registry,
        supervisors=["main"],
        llm_provider=lambda: None,
        supervisor_factory=supervisor_factory,
        enable_subgraphs=True,
        supervisor_allowlists=allowlists,
    )
    graph.set_entry_point("main_supervisor")
    return graph.compile()


@pytest.mark.asyncio
async def test_call_subgraph_executes_child(registry):
    compiled = _build_subgraph_graph(registry)
    state = {"request": {}, "response": {}, "_internal": {}}
    result = await compiled.ainvoke(state)

    assert result["response"]["response_type"] == "child_done"
    internal = result.get("_internal", {})
    assert internal.get("call_stack", []) == []
    visited = internal.get("visited_subgraphs", {})
    assert visited.get("child_graph") == 1
    trace = internal.get("decision_trace", [])
    assert any(item.get("decision_kind") == "SUBGRAPH" for item in trace)
    assert any(
        item.get("decision_kind") == "SUBGRAPH" and item.get("target") == "child_graph"
        for item in trace
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "budgets,expected_reason",
    [
        ({"max_depth": 0, "max_steps": 40, "max_reentry": 2}, "max_depth_exceeded"),
        ({"max_depth": 2, "max_steps": 0, "max_reentry": 2}, "max_steps_exceeded"),
        ({"max_depth": 2, "max_steps": 40, "max_reentry": 0}, "cycle_detected"),
    ],
)
async def test_call_subgraph_budgets_stop(registry, budgets, expected_reason):
    compiled = _build_subgraph_graph(registry)
    state = {"request": {}, "response": {}, "_internal": {"budgets": budgets}}
    result = await compiled.ainvoke(state)

    assert result["response"]["response_type"] == "terminal"
    trace = result.get("_internal", {}).get("decision_trace", [])
    assert any(item.get("termination_reason") == expected_reason for item in trace)


@pytest.mark.asyncio
async def test_allowlist_violation_stops(registry):
    compiled = _build_subgraph_graph(registry, allowlists={"main": {"done"}})
    state = {"request": {}, "response": {}, "_internal": {}}
    result = await compiled.ainvoke(state)

    assert result["response"]["response_type"] == "terminal"
    trace = result.get("_internal", {}).get("decision_trace", [])
    assert any(item.get("termination_reason") == "allowlist_violation" for item in trace)
