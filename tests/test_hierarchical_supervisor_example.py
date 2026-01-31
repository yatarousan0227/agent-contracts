import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.hierarchical_supervisor_minimal.main import build_graph


@pytest.mark.asyncio
async def test_hierarchical_example_runs():
    compiled = build_graph()
    result = await compiled.ainvoke(
        {
            "request": {"action": "fashion", "message": "Fall collection"},
            "response": {},
            "_internal": {},
        }
    )

    # For StateGraph(dict), wrappers must return full state so request persists.
    request = result.get("request", {})
    assert request.get("message") == "Fall collection"

    response = result.get("response", {})
    assert response.get("response_type") == "fashion_trend"
    assert "Fall collection" in (response.get("response_message") or "")
    internal = result.get("_internal", {})
    visited = internal.get("visited_subgraphs", {})
    assert visited.get("fashion") == 1
    trace = internal.get("decision_trace", [])
    assert any(item.get("decision_kind") == "SUBGRAPH" for item in trace)
