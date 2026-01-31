"""Tests for nested CallSubgraph execution and subgraph entrypoint variants."""

import pytest

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


class GrandchildNode(ModularNode):
    """Terminal node inside the grandchild subgraph."""

    CONTRACT = NodeContract(
        name="grandchild_node",
        description="Grandchild subgraph node",
        reads=["request"],
        writes=["response"],
        supervisor="grandchild",
        is_terminal=True,
        trigger_conditions=[TriggerCondition(priority=1)],
    )

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(
            response={
                "response_type": "grandchild_done",
                "response_data": {"grandchild": True},
            }
        )


class EntrypointNode(ModularNode):
    """Terminal node used as a subgraph entrypoint."""

    CONTRACT = NodeContract(
        name="entrypoint_node",
        description="Subgraph node entrypoint",
        reads=["request"],
        writes=["response"],
        supervisor="child",
        is_terminal=True,
        trigger_conditions=[TriggerCondition(priority=1)],
    )

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(
            response={
                "response_type": "entrypoint_done",
                "response_data": {"entrypoint": True},
            }
        )


class ParentSupervisor:
    """Minimal supervisor that calls a subgraph once, then stops."""

    def __init__(self, target: str) -> None:
        self.target = target

    async def run(self, state: dict, config=None) -> dict:
        internal = state.get("_internal", {})
        response = state.get("response", {})
        response_type = response.get("response_type") if isinstance(response, dict) else None
        if response_type in {"grandchild_done", "entrypoint_done", "terminal"}:
            decision = "done"
        else:
            decision = self.target
        return {
            "_internal": {
                **(internal if isinstance(internal, dict) else {}),
                "decision": decision,
            }
        }


class ChildSupervisor:
    """Subgraph supervisor that calls another subgraph once, then stops."""

    def __init__(self, target: str) -> None:
        self.target = target

    async def run(self, state: dict, config=None) -> dict:
        internal = state.get("_internal", {})
        response = state.get("response", {})
        response_type = response.get("response_type") if isinstance(response, dict) else None
        if response_type in {"grandchild_done", "terminal"}:
            decision = "done"
        else:
            decision = self.target
        return {
            "_internal": {
                **(internal if isinstance(internal, dict) else {}),
                "decision": decision,
            }
        }


def _build_nested_registry() -> NodeRegistry:
    registry = NodeRegistry()
    registry.register(GrandchildNode)

    grandchild_contract = SubgraphContract(
        subgraph_id="grandchild_graph",
        description="Grandchild subgraph",
        reads=["request"],
        writes=["response"],
        entrypoint="grandchild",
    )
    grandchild_definition = SubgraphDefinition(
        subgraph_id="grandchild_graph",
        supervisors=["grandchild"],
        nodes=["grandchild_node"],
    )
    registry.register_subgraph(grandchild_contract, grandchild_definition)

    child_contract = SubgraphContract(
        subgraph_id="child_graph",
        description="Child subgraph that calls grandchild",
        reads=["request"],
        writes=["response"],
        entrypoint="child",
    )
    child_definition = SubgraphDefinition(
        subgraph_id="child_graph",
        supervisors=["child"],
        nodes=[],
    )
    registry.register_subgraph(child_contract, child_definition)

    return registry


def _build_nested_graph(registry: NodeRegistry):
    def supervisor_factory(name: str, llm):
        if name == "main":
            return ParentSupervisor("call_subgraph::child_graph")
        if name == "child":
            return ChildSupervisor("call_subgraph::grandchild_graph")
        if name == "grandchild":
            return GenericSupervisor(
                supervisor_name=name,
                llm=None,
                registry=registry,
            )
        raise AssertionError(f"Unexpected supervisor: {name}")

    graph = build_graph_from_registry(
        registry=registry,
        supervisors=["main"],
        llm_provider=lambda: None,
        supervisor_factory=supervisor_factory,
        enable_subgraphs=True,
    )
    graph.set_entry_point("main_supervisor")
    return graph.compile()


@pytest.mark.asyncio
async def test_nested_call_subgraph_executes_and_returns():
    registry = _build_nested_registry()
    compiled = _build_nested_graph(registry)
    result = await compiled.ainvoke({"request": {}, "response": {}, "_internal": {}})

    assert result["response"]["response_type"] == "grandchild_done"
    internal = result.get("_internal", {})
    assert internal.get("call_stack", []) == []
    visited = internal.get("visited_subgraphs", {})
    assert visited.get("child_graph") == 1
    assert visited.get("grandchild_graph") == 1

    trace = internal.get("decision_trace", [])
    assert any(
        item.get("decision_kind") == "SUBGRAPH"
        and item.get("target") == "child_graph"
        and item.get("depth") == 0
        for item in trace
    )
    assert any(
        item.get("decision_kind") == "SUBGRAPH"
        and item.get("target") == "grandchild_graph"
        and item.get("depth") == 1
        for item in trace
    )


@pytest.mark.asyncio
async def test_nested_call_subgraph_respects_max_depth_budget():
    registry = _build_nested_registry()
    compiled = _build_nested_graph(registry)
    result = await compiled.ainvoke(
        {
            "request": {},
            "response": {},
            "_internal": {"budgets": {"max_depth": 1, "max_steps": 40, "max_reentry": 2}},
        }
    )

    assert result["response"]["response_type"] == "terminal"
    trace = result.get("_internal", {}).get("decision_trace", [])
    assert any(item.get("termination_reason") == "max_depth_exceeded" for item in trace)
    assert result.get("_internal", {}).get("call_stack", []) == []


@pytest.mark.asyncio
async def test_subgraph_entrypoint_can_be_node():
    registry = NodeRegistry()
    registry.register(EntrypointNode)

    child_contract = SubgraphContract(
        subgraph_id="child_graph",
        description="Child subgraph with node entrypoint",
        reads=["request"],
        writes=["response"],
        entrypoint="entrypoint_node",
    )
    child_definition = SubgraphDefinition(
        subgraph_id="child_graph",
        supervisors=["child"],
        nodes=["entrypoint_node"],
    )
    registry.register_subgraph(child_contract, child_definition)

    def supervisor_factory(name: str, llm):
        if name == "main":
            return ParentSupervisor("call_subgraph::child_graph")
        if name == "child":
            return GenericSupervisor(
                supervisor_name=name,
                llm=None,
                registry=registry,
            )
        raise AssertionError(f"Unexpected supervisor: {name}")

    graph = build_graph_from_registry(
        registry=registry,
        supervisors=["main"],
        llm_provider=lambda: None,
        supervisor_factory=supervisor_factory,
        enable_subgraphs=True,
    )
    graph.set_entry_point("main_supervisor")
    compiled = graph.compile()

    result = await compiled.ainvoke({"request": {}, "response": {}, "_internal": {}})
    assert result["response"]["response_type"] == "entrypoint_done"
    assert result.get("_internal", {}).get("call_stack", []) == []
    visited = result.get("_internal", {}).get("visited_subgraphs", {})
    assert visited.get("child_graph") == 1

