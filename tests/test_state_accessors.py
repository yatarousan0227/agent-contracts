"""Tests for state_accessors module."""
import pytest

from agent_contracts.state_accessors import (
    StateAccessor,
    Internal,
    Request,
    Response,
    reset_response,
    increment_turn,
    set_error,
    clear_error,
)
from agent_contracts import Budgets


class TestStateAccessor:
    """Tests for StateAccessor class."""

    def test_get_from_empty_state(self):
        """Get from empty state returns default."""
        accessor = StateAccessor("_internal", "turn_count", 0)
        state = {}
        assert accessor.get(state) == 0

    def test_get_from_missing_slice(self):
        """Get from missing slice returns default."""
        accessor = StateAccessor("_internal", "turn_count", 0)
        state = {"request": {}}
        assert accessor.get(state) == 0

    def test_get_existing_value(self):
        """Get existing value returns it."""
        accessor = StateAccessor("_internal", "turn_count", 0)
        state = {"_internal": {"turn_count": 5}}
        assert accessor.get(state) == 5

    def test_set_creates_slice(self):
        """Set creates slice if missing."""
        accessor = StateAccessor("_internal", "turn_count", 0)
        state = {}
        new_state = accessor.set(state, 10)
        
        assert new_state == {"_internal": {"turn_count": 10}}
        assert state == {}  # Original unchanged

    def test_set_preserves_other_fields(self):
        """Set preserves other fields in slice."""
        accessor = StateAccessor("_internal", "turn_count", 0)
        state = {"_internal": {"error": "some error", "turn_count": 1}}
        new_state = accessor.set(state, 10)
        
        assert new_state == {"_internal": {"error": "some error", "turn_count": 10}}

    def test_set_preserves_other_slices(self):
        """Set preserves other slices."""
        accessor = StateAccessor("_internal", "turn_count", 0)
        state = {"request": {"action": "test"}, "_internal": {"turn_count": 1}}
        new_state = accessor.set(state, 10)
        
        assert new_state["request"] == {"action": "test"}
        assert new_state["_internal"]["turn_count"] == 10

    def test_set_is_immutable(self):
        """Set does not mutate original state."""
        accessor = StateAccessor("_internal", "turn_count", 0)
        state = {"_internal": {"turn_count": 5}}
        new_state = accessor.set(state, 10)
        
        assert state["_internal"]["turn_count"] == 5
        assert new_state["_internal"]["turn_count"] == 10

    def test_update_with_function(self):
        """Update applies function to current value."""
        accessor = StateAccessor("_internal", "turn_count", 0)
        state = {"_internal": {"turn_count": 5}}
        new_state = accessor.update(state, lambda x: x + 1)
        
        assert new_state["_internal"]["turn_count"] == 6
        assert state["_internal"]["turn_count"] == 5

    def test_update_from_default(self):
        """Update uses default if value missing."""
        accessor = StateAccessor("_internal", "turn_count", 0)
        state = {}
        new_state = accessor.update(state, lambda x: x + 1)
        
        assert new_state["_internal"]["turn_count"] == 1

    def test_repr(self):
        """Repr shows useful info."""
        accessor = StateAccessor("_internal", "turn_count", 0)
        assert "StateAccessor" in repr(accessor)
        assert "_internal" in repr(accessor)
        assert "turn_count" in repr(accessor)


class TestInternalAccessors:
    """Tests for Internal slice accessors."""

    def test_turn_count(self):
        """turn_count accessor works."""
        state = {"_internal": {"turn_count": 3}}
        assert Internal.turn_count.get(state) == 3
        
        new_state = Internal.turn_count.set(state, 5)
        assert Internal.turn_count.get(new_state) == 5

    def test_is_first_turn(self):
        """is_first_turn accessor works."""
        state = {}
        assert Internal.is_first_turn.get(state) is True
        
        new_state = Internal.is_first_turn.set(state, False)
        assert Internal.is_first_turn.get(new_state) is False

    def test_active_mode(self):
        """active_mode accessor works."""
        state = {}
        assert Internal.active_mode.get(state) is None
        
        new_state = Internal.active_mode.set(state, "shopping")
        assert Internal.active_mode.get(new_state) == "shopping"

    def test_error(self):
        """error accessor works."""
        state = {}
        assert Internal.error.get(state) is None
        
        new_state = Internal.error.set(state, "Something went wrong")
        assert Internal.error.get(new_state) == "Something went wrong"

    def test_call_stack(self):
        """call_stack accessor works."""
        state = {}
        assert Internal.call_stack.get(state) == []
        
        new_state = Internal.call_stack.set(state, [{"subgraph_id": "sg1"}])
        assert Internal.call_stack.get(new_state) == [{"subgraph_id": "sg1"}]

    def test_budgets(self):
        """budgets accessor works."""
        state = {}
        assert Internal.budgets.get(state) is None
        
        budgets = Budgets(max_depth=3, max_steps=10, max_reentry=1)
        new_state = Internal.budgets.set(state, budgets)
        assert Internal.budgets.get(new_state) == budgets

    def test_decision_trace(self):
        """decision_trace accessor works."""
        state = {}
        assert Internal.decision_trace.get(state) == []
        
        new_state = Internal.decision_trace.set(state, [{"step": 1, "decision_kind": "NODE"}])
        assert Internal.decision_trace.get(new_state) == [{"step": 1, "decision_kind": "NODE"}]

    def test_visited_subgraphs(self):
        """visited_subgraphs accessor works."""
        state = {}
        assert Internal.visited_subgraphs.get(state) == {}
        
        new_state = Internal.visited_subgraphs.set(state, {"sg1": 1})
        assert Internal.visited_subgraphs.get(new_state) == {"sg1": 1}

    def test_step_count(self):
        """step_count accessor works."""
        state = {}
        assert Internal.step_count.get(state) == 0
        
        new_state = Internal.step_count.set(state, 2)
        assert Internal.step_count.get(new_state) == 2


class TestRequestAccessors:
    """Tests for Request slice accessors."""

    def test_session_id(self):
        """session_id accessor works."""
        state = {"request": {"session_id": "abc123"}}
        assert Request.session_id.get(state) == "abc123"

    def test_action(self):
        """action accessor works."""
        state = {"request": {"action": "answer"}}
        assert Request.action.get(state) == "answer"

    def test_params(self):
        """params accessor works."""
        state = {"request": {"params": {"key": "value"}}}
        assert Request.params.get(state) == {"key": "value"}

    def test_message(self):
        """message accessor works."""
        state = {"request": {"message": "Hello"}}
        assert Request.message.get(state) == "Hello"


class TestResponseAccessors:
    """Tests for Response slice accessors."""

    def test_response_type(self):
        """response_type accessor works."""
        state = {"response": {"response_type": "interview"}}
        assert Response.response_type.get(state) == "interview"

    def test_response_data(self):
        """response_data accessor works."""
        state = {"response": {"response_data": {"question": "Test?"}}}
        assert Response.response_data.get(state) == {"question": "Test?"}


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_reset_response(self):
        """reset_response clears all response fields."""
        state = {
            "response": {
                "response_type": "interview",
                "response_data": {"q": "test"},
                "response_message": "Hello",
            }
        }
        new_state = reset_response(state)
        
        assert Response.response_type.get(new_state) is None
        assert Response.response_data.get(new_state) is None
        assert Response.response_message.get(new_state) is None

    def test_increment_turn(self):
        """increment_turn increases count and sets is_first_turn."""
        state = {"_internal": {"turn_count": 0, "is_first_turn": True}}
        new_state = increment_turn(state)
        
        assert Internal.turn_count.get(new_state) == 1
        assert Internal.is_first_turn.get(new_state) is False

    def test_set_error(self):
        """set_error sets error field."""
        state = {}
        new_state = set_error(state, "Test error")
        assert Internal.error.get(new_state) == "Test error"

    def test_clear_error(self):
        """clear_error clears error field."""
        state = {"_internal": {"error": "Some error"}}
        new_state = clear_error(state)
        assert Internal.error.get(new_state) is None


class TestImmutability:
    """Tests to verify immutability guarantees."""

    def test_chained_sets_are_immutable(self):
        """Chained set operations don't affect intermediate states."""
        state = {}
        state1 = Internal.turn_count.set(state, 1)
        state2 = Internal.turn_count.set(state1, 2)
        state3 = Internal.turn_count.set(state2, 3)
        
        assert Internal.turn_count.get(state) == 0
        assert Internal.turn_count.get(state1) == 1
        assert Internal.turn_count.get(state2) == 2
        assert Internal.turn_count.get(state3) == 3

    def test_nested_dicts_are_copied(self):
        """Nested dicts are shallow copied."""
        state = {"_internal": {"turn_count": 1, "nested": {"value": "original"}}}
        new_state = Internal.turn_count.set(state, 2)
        
        # Different dict objects
        assert state["_internal"] is not new_state["_internal"]
