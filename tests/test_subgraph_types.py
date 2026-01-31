"""Tests for subgraph and hierarchy core types."""
from dataclasses import asdict

from pydantic import BaseModel

from agent_contracts import (
    SubgraphContract,
    SubgraphDefinition,
    Budgets,
    CallStackFrame,
    DecisionTraceItem,
)


class SampleInput(BaseModel):
    """Sample input schema."""
    query: str


class SampleOutput(BaseModel):
    """Sample output schema."""
    result: str


class TestSubgraphTypes:
    """Tests for subgraph contract models."""

    def test_subgraph_contract_creation(self):
        """SubgraphContract should be created correctly."""
        contract = SubgraphContract(
            subgraph_id="search_flow",
            description="Search subgraph",
            reads=["request"],
            writes=["response"],
            entrypoint="search_supervisor",
            input_schema=SampleInput,
            output_schema=SampleOutput,
        )
        assert contract.subgraph_id == "search_flow"
        assert contract.reads == ["request"]
        assert contract.writes == ["response"]
        assert contract.entrypoint == "search_supervisor"
        assert contract.input_schema is SampleInput
        assert contract.output_schema is SampleOutput

        payload = contract.model_dump()
        assert payload["subgraph_id"] == "search_flow"
        assert payload["entrypoint"] == "search_supervisor"

    def test_subgraph_definition_creation(self):
        """SubgraphDefinition should be created correctly."""
        definition = SubgraphDefinition(
            subgraph_id="search_flow",
            supervisors=["search_supervisor"],
            nodes=["search_node", "rank_node"],
        )
        assert definition.subgraph_id == "search_flow"
        assert definition.supervisors == ["search_supervisor"]
        assert definition.nodes == ["search_node", "rank_node"]


class TestHierarchyRuntimeTypes:
    """Tests for hierarchy runtime dataclasses."""

    def test_budgets_defaults(self):
        """Budgets should have default values."""
        budgets = Budgets()
        assert budgets.max_depth == 2
        assert budgets.max_steps == 40
        assert budgets.max_reentry == 2

    def test_call_stack_frame_serialization(self):
        """CallStackFrame should serialize via asdict."""
        frame = CallStackFrame(
            subgraph_id="search_flow",
            depth=1,
            entry_step=3,
            locals={"query": "shoes"},
        )
        assert asdict(frame) == {
            "subgraph_id": "search_flow",
            "depth": 1,
            "entry_step": 3,
            "locals": {"query": "shoes"},
        }

    def test_decision_trace_item_serialization(self):
        """DecisionTraceItem should serialize via asdict."""
        item = DecisionTraceItem(
            step=5,
            depth=1,
            supervisor="search_supervisor",
            decision_kind="NODE",
            target="search_node",
            reason="matched rule",
            termination_reason=None,
        )
        assert asdict(item) == {
            "step": 5,
            "depth": 1,
            "supervisor": "search_supervisor",
            "decision_kind": "NODE",
            "target": "search_node",
            "reason": "matched rule",
            "termination_reason": None,
        }
