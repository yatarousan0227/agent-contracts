# Hierarchical Supervisor Minimal Example

A minimal example that demonstrates a parent supervisor calling a child subgraph and returning.

## Quick Start

```bash
# From the project root
python -m examples.hierarchical_supervisor_minimal
```

## What It Does

- The **Domain supervisor** routes to a subgraph when `request.action == "fashion"`.
- The **fashion subgraph** runs a child supervisor that executes `TrendNode`.
- The child node writes a response and the subgraph ends, returning to the parent.

## Key Concepts

- **CallSubgraph decision**: The parent supervisor returns `call_subgraph::fashion`.
- **Subgraph registration**: `SubgraphContract` + `SubgraphDefinition` declare the child graph.
- **Return to parent**: The CallSubgraph wrapper routes back to the parent supervisor.

## Files

```
examples/hierarchical_supervisor_minimal/
├── __init__.py
├── __main__.py
├── main.py
└── README.md
```

## Related Tests (E2E)

For more exhaustive hierarchical coverage (budgets / allowlists / nesting / node-entrypoint):

```bash
./.venv/bin/pytest -q tests/test_graph_builder_subgraph.py
./.venv/bin/pytest -q tests/test_graph_builder_subgraph_nested.py
./.venv/bin/pytest -q tests/test_hierarchical_supervisor_example.py
```

## Optional: Budgets / Safe Stop

You can limit depth, steps, and re-entry with `_internal.budgets`:

```python
state = {
    "request": {"action": "fashion", "message": "Fall collection"},
    "response": {},
    "_internal": {
        "budgets": {"max_depth": 2, "max_steps": 40, "max_reentry": 1}
    },
}
```
