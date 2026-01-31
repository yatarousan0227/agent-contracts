"""Tests for runtime/streaming module."""
import pytest
from unittest.mock import AsyncMock

from agent_contracts.runtime.streaming import (
    StreamEvent,
    StreamEventType,
    NodeExecutor,
    StreamingRuntime,
    create_status_event,
    create_progress_event,
    create_data_event,
)
from agent_contracts.runtime.context import RequestContext
from agent_contracts.state_accessors import Response


class TestStreamEvent:
    """Tests for StreamEvent dataclass."""

    def test_basic_creation(self):
        """Basic event creation works."""
        event = StreamEvent(
            type=StreamEventType.NODE_START,
            node_name="search",
        )
        assert event.type == StreamEventType.NODE_START
        assert event.node_name == "search"
        assert event.data is None

    def test_full_creation(self):
        """Full event with all fields works."""
        event = StreamEvent(
            type=StreamEventType.NODE_END,
            node_name="search",
            data={"count": 10},
            message="Search complete",
            state={"response": {}},
        )
        assert event.data == {"count": 10}
        assert event.message == "Search complete"
        assert event.state == {"response": {}}

    def test_to_dict(self):
        """to_dict serializes correctly."""
        event = StreamEvent(
            type=StreamEventType.NODE_END,
            node_name="search",
            data={"count": 10},
            message="Done",
        )
        result = event.to_dict()
        
        assert result["type"] == "node_end"
        assert result["node_name"] == "search"
        assert result["data"] == {"count": 10}
        assert result["message"] == "Done"

    def test_to_dict_minimal(self):
        """to_dict with minimal fields."""
        event = StreamEvent(type=StreamEventType.STATUS)
        result = event.to_dict()
        
        assert result == {"type": "status"}

    def test_to_sse(self):
        """to_sse formats correctly."""
        event = StreamEvent(
            type=StreamEventType.NODE_END,
            node_name="search",
            data={"count": 10},
        )
        sse = event.to_sse()
        
        assert sse.startswith("event: node_end\n")
        assert "data: " in sse
        assert sse.endswith("\n\n")

    def test_string_type(self):
        """String type works."""
        event = StreamEvent(type="custom_event")
        result = event.to_dict()
        assert result["type"] == "custom_event"


class TestNodeExecutor:
    """Tests for NodeExecutor dataclass."""

    def test_creation(self):
        """Basic creation works."""
        async def my_node(state):
            return {"response": {"done": True}}
        
        executor = NodeExecutor(
            name="my_node",
            func=my_node,
            description="Does something",
        )
        
        assert executor.name == "my_node"
        assert executor.func == my_node
        assert executor.description == "Does something"


class TestStreamingRuntime:
    """Tests for StreamingRuntime."""

    @pytest.mark.asyncio
    async def test_stream_basic(self):
        """Basic streaming with nodes works."""
        # Mock nodes
        node1 = AsyncMock(return_value={"response": {"step": 1}})
        node2 = AsyncMock(return_value={"response": {"step": 2}})
        
        runtime = StreamingRuntime(nodes=[
            NodeExecutor("node1", node1),
            NodeExecutor("node2", node2),
        ])
        
        events = []
        async for event in runtime.stream(RequestContext(
            session_id="abc",
            action="test",
        )):
            events.append(event)
        
        # Should have: 2x (start + end) + done = 5 events
        assert len(events) == 5
        assert events[0].type == StreamEventType.NODE_START
        assert events[0].node_name == "node1"
        assert events[1].type == StreamEventType.NODE_END
        assert events[4].type == StreamEventType.DONE

    @pytest.mark.asyncio
    async def test_stream_with_initial_state(self):
        """Streaming with pre-built initial state."""
        node = AsyncMock(return_value=None)
        
        runtime = StreamingRuntime(nodes=[
            NodeExecutor("node", node),
        ])
        
        initial_state = {"custom": {"data": "test"}}
        events = []
        async for event in runtime.stream(
            RequestContext(session_id="abc", action="test"),
            initial_state=initial_state,
        ):
            events.append(event)
        
        # Node should have been called with initial state
        call_args = node.call_args[0][0]
        assert call_args.get("custom") == {"data": "test"}

    @pytest.mark.asyncio
    async def test_stream_handles_error(self):
        """Streaming handles node errors gracefully."""
        failing_node = AsyncMock(side_effect=RuntimeError("Node failed"))
        
        runtime = StreamingRuntime(nodes=[
            NodeExecutor("failing", failing_node),
        ])
        
        events = []
        async for event in runtime.stream(RequestContext(
            session_id="abc",
            action="test",
        )):
            events.append(event)
        
        # Should have: start + error = 2 events
        assert len(events) == 2
        assert events[0].type == StreamEventType.NODE_START
        assert events[1].type == StreamEventType.ERROR
        assert "Node failed" in events[1].message

    @pytest.mark.asyncio
    async def test_stream_applies_updates(self):
        """Node updates are applied to state."""
        node1 = AsyncMock(return_value={"response": {"response_type": "step1"}})
        node2 = AsyncMock(return_value={"response": {"response_data": {"value": 42}}})
        
        runtime = StreamingRuntime(nodes=[
            NodeExecutor("node1", node1),
            NodeExecutor("node2", node2),
        ])
        
        events = []
        async for event in runtime.stream(RequestContext(
            session_id="abc",
            action="test",
        )):
            events.append(event)
        
        # Check final done event
        done_event = events[-1]
        assert done_event.type == StreamEventType.DONE
        assert done_event.data["type"] == "step1"
        assert done_event.data["value"] == 42

    @pytest.mark.asyncio
    async def test_add_node_fluent(self):
        """Fluent add_node API works."""
        node1 = AsyncMock(return_value=None)
        node2 = AsyncMock(return_value=None)
        
        runtime = (
            StreamingRuntime()
            .add_node("node1", node1)
            .add_node("node2", node2, description="Second node")
        )
        
        assert len(runtime.nodes) == 2
        assert runtime.nodes[0].name == "node1"
        assert runtime.nodes[1].name == "node2"
        assert runtime.nodes[1].description == "Second node"

    @pytest.mark.asyncio
    async def test_stream_with_hooks(self):
        """Hooks are called during streaming."""
        node = AsyncMock(return_value=None)
        
        class TestHooks:
            def __init__(self):
                self.prepare_called = False
                self.after_called = False
            
            async def prepare_state(self, state, request):
                self.prepare_called = True
                return state
            
            async def after_execution(self, state, result):
                self.after_called = True
        
        hooks = TestHooks()
        runtime = StreamingRuntime(
            nodes=[NodeExecutor("node", node)],
            hooks=hooks,
        )
        
        events = []
        async for event in runtime.stream(RequestContext(
            session_id="abc",
            action="test",
        )):
            events.append(event)
        
        assert hooks.prepare_called is True
        assert hooks.after_called is True


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_create_status_event(self):
        """create_status_event works."""
        event = create_status_event("Processing...")
        
        assert event.type == StreamEventType.STATUS
        assert event.message == "Processing..."

    def test_create_progress_event(self):
        """create_progress_event works."""
        event = create_progress_event(5, 10, "Halfway there")
        
        assert event.type == StreamEventType.PROGRESS
        assert event.data == {"current": 5, "total": 10}
        assert event.message == "Halfway there"

    def test_create_data_event(self):
        """create_data_event works."""
        event = create_data_event({"results": [1, 2, 3]}, "Results ready")
        
        assert event.type == StreamEventType.DATA
        assert event.data == {"results": [1, 2, 3]}
        assert event.message == "Results ready"


class TestStreamingRuntimeSessionRestore:
    """Tests for session restoration in StreamingRuntime."""

    @pytest.mark.asyncio
    async def test_stream_with_session_restore(self):
        """Streaming restores session data when resume_session is True."""
        node = AsyncMock(return_value=None)
        
        # Mock session store
        class MockSessionStore:
            async def load(self, session_id):
                return {"shopping": {"search_count": 5}}
            
            async def save(self, session_id, data, ttl=3600):
                pass
        
        runtime = StreamingRuntime(
            nodes=[NodeExecutor("node", node)],
            session_store=MockSessionStore(),
            slices_to_restore=["shopping"],
        )
        
        events = []
        async for event in runtime.stream(RequestContext(
            session_id="abc",
            action="test",
            resume_session=True,
        )):
            events.append(event)
        
        # Node should have been called with restored session data
        call_args = node.call_args[0][0]
        assert call_args.get("shopping", {}).get("search_count") == 5

    @pytest.mark.asyncio
    async def test_stream_without_session_data(self):
        """Streaming handles missing session data gracefully."""
        node = AsyncMock(return_value=None)
        
        class MockSessionStore:
            async def load(self, session_id):
                return None
        
        runtime = StreamingRuntime(
            nodes=[NodeExecutor("node", node)],
            session_store=MockSessionStore(),
        )
        
        events = []
        async for event in runtime.stream(RequestContext(
            session_id="abc",
            action="test",
            resume_session=True,
        )):
            events.append(event)
        
        # Should complete without error
        assert events[-1].type == StreamEventType.DONE


class TestStreamingRuntimeWithGraph:
    """Tests for stream_with_graph method."""

    @pytest.mark.asyncio
    async def test_stream_with_graph_updates_mode(self):
        """stream_with_graph works with updates mode."""
        runtime = StreamingRuntime()
        
        # Mock graph with astream
        class MockGraph:
            async def astream(self, state, stream_mode="updates", **kwargs):
                yield {"node1": {"response": {"type": "test"}}}
                yield {"node2": {"data": "value"}}
        
        events = []
        async for event in runtime.stream_with_graph(
            RequestContext(session_id="abc", action="test"),
            graph=MockGraph(),
            stream_mode="updates",
        ):
            events.append(event)
        
        assert len(events) >= 2  # At least 2 node events + done
        assert events[-1].type == StreamEventType.DONE

    @pytest.mark.asyncio
    async def test_stream_with_graph_initial_state(self):
        """stream_with_graph accepts an initial state override."""
        runtime = StreamingRuntime()

        class MockGraph:
            def __init__(self):
                self.seen_state = None

            async def astream(self, state, stream_mode="updates", **kwargs):
                self.seen_state = state
                yield {"node1": {"response": {"response_type": "test"}}}

        graph = MockGraph()
        initial_state = {"custom": {"data": "test"}}

        events = []
        async for event in runtime.stream_with_graph(
            RequestContext(session_id="abc", action="test"),
            graph=graph,
            initial_state=initial_state,
        ):
            events.append(event)

        assert graph.seen_state.get("custom") == {"data": "test"}
        assert events[-1].type == StreamEventType.DONE

    @pytest.mark.asyncio
    async def test_stream_with_graph_values_mode(self):
        """stream_with_graph works with values mode."""
        runtime = StreamingRuntime()
        
        class MockGraph:
            async def astream(self, state, stream_mode="values", **kwargs):
                yield {"response": {"response_type": "interview"}}
        
        events = []
        async for event in runtime.stream_with_graph(
            RequestContext(session_id="abc", action="test"),
            graph=MockGraph(),
            stream_mode="values",
        ):
            events.append(event)
        
        assert len(events) >= 1
        assert events[-1].type == StreamEventType.DONE

    @pytest.mark.asyncio
    async def test_stream_with_graph_error_handling(self):
        """stream_with_graph handles errors gracefully."""
        runtime = StreamingRuntime()
        
        class FailingGraph:
            async def astream(self, state, stream_mode="updates", **kwargs):
                raise RuntimeError("Graph failed")
                yield  # Make it a generator
        
        events = []
        async for event in runtime.stream_with_graph(
            RequestContext(session_id="abc", action="test"),
            graph=FailingGraph(),
        ):
            events.append(event)
        
        assert events[-1].type == StreamEventType.ERROR
        assert "Graph failed" in events[-1].message

    @pytest.mark.asyncio
    async def test_stream_with_graph_session_restore(self):
        """stream_with_graph restores session data."""
        class MockSessionStore:
            async def load(self, session_id):
                return {"shopping": {"restored": True}}
        
        class MockGraph:
            async def astream(self, state, stream_mode="updates", **kwargs):
                # Return the state to verify restoration
                yield {"result": {"state": state}}
        
        runtime = StreamingRuntime(
            session_store=MockSessionStore(),
            slices_to_restore=["shopping"],
        )
        
        events = []
        async for event in runtime.stream_with_graph(
            RequestContext(session_id="abc", action="test", resume_session=True),
            graph=MockGraph(),
        ):
            events.append(event)
        
        assert events[-1].type == StreamEventType.DONE

    @pytest.mark.asyncio
    async def test_stream_with_graph_include_subgraphs(self):
        """stream_with_graph includes subgraph events when include_subgraphs=True."""
        runtime = StreamingRuntime()
        
        # Mock graph that returns subgraph-style events (namespace, data) tuples
        class MockGraphWithSubgraphs:
            async def astream(self, state, stream_mode="updates", subgraphs=True):
                # Simulate parent graph node
                yield ((), {"parent_node": {"response": {"type": "parent"}}})
                # Simulate subgraph node (namespace shows path)
                yield (("subgraph:abc123",), {"child_node": {"data": "from_subgraph"}})
                # Simulate nested subgraph
                yield (("subgraph:abc123", "nested:def456"), {"deep_node": {"data": "nested"}})
        
        events = []
        async for event in runtime.stream_with_graph(
            RequestContext(session_id="abc", action="test"),
            graph=MockGraphWithSubgraphs(),
            stream_mode="updates",
            include_subgraphs=True,
        ):
            events.append(event)
        
        # Should have 3 node_end events + done
        node_events = [e for e in events if e.type == StreamEventType.NODE_END]
        assert len(node_events) == 3
        
        # Check node names include subgraph path
        node_names = [e.node_name for e in node_events]
        assert "parent_node" in node_names
        assert "child_node::subgraph" in node_names
        assert "deep_node::subgraph::nested" in node_names
        
        assert events[-1].type == StreamEventType.DONE
