# ヒエラリカル Supervisor ガイド (v0.6.0)

このガイドは、親SupervisorからSubgraphを呼び出し、子グラフ終了後に親へ戻る方法と、安全停止の仕組みを説明します。

## 概要

ヒエラリカル実行は **opt-in** です。親Supervisorは次の文字列を返すことで
**CallSubgraph** ノードへ遷移します。

```
call_subgraph::<subgraph_id>
```

CallSubgraphは子グラフを実行し、子が `END` に到達すると親Supervisorへ戻ります。

ノード名に予約プレフィックス `call_subgraph::` は使用できません。

## 最小構成

1) 子ノードを定義して登録
2) Subgraph contract/definition を登録
3) `enable_subgraphs=True` でグラフをビルド
4) 親Supervisorから Subgraph へルーティング

```python
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
    CONTRACT = NodeContract(
        name="trend_node",
        description="Return a fashion trend",
        reads=["request"],
        writes=["response"],
        supervisor="fashion",
        is_terminal=True,
        trigger_conditions=[TriggerCondition(priority=1)],
    )

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        return NodeOutputs(
            response={"response_type": "fashion_trend", "response_message": "..."}
        )

registry = NodeRegistry()
registry.register(TrendNode)

registry.register_subgraph(
    SubgraphContract(
        subgraph_id="fashion",
        description="Fashion trend subgraph",
        reads=["request"],
        writes=["response"],
        entrypoint="fashion",
    ),
    SubgraphDefinition(
        subgraph_id="fashion",
        supervisors=["fashion"],
        nodes=["trend_node"],
    ),
)


def route_domain(state: dict) -> str | None:
    return "call_subgraph::fashion"


def supervisor_factory(name: str, llm):
    if name == "domain":
        return GenericSupervisor(
            supervisor_name=name,
            llm=None,
            registry=registry,
            explicit_routing_handler=route_domain,
        )
    return GenericSupervisor(supervisor_name=name, llm=None, registry=registry)


graph = build_graph_from_registry(
    registry=registry,
    supervisors=["domain"],
    llm_provider=lambda: None,
    supervisor_factory=supervisor_factory,
    enable_subgraphs=True,
)
```

実行できる最小例は次にあります:

- `examples/hierarchical_supervisor_minimal/`

## STOP_LOCAL / STOP_GLOBAL

- **STOP_LOCAL**: 子Subgraphを終了し、親Supervisorに復帰します。
  - 子グラフが `END` に到達すると、CallSubgraphが親に戻します。
- **STOP_GLOBAL**: セッション全体を終了します。
  - terminal response や安全停止、allowlist違反で発生します。

## Budgets / Cycle Detection

CallSubgraphは `_internal.budgets` の制限を適用します。

- `max_depth` (default: 2)
- `max_steps` (default: 40)
- `max_reentry` (default: 2)

例:

```python
state = {
    "request": {"action": "fashion"},
    "response": {},
    "_internal": {
        "budgets": {"max_depth": 1, "max_steps": 20, "max_reentry": 1}
    },
}
```

制限に到達すると安全停止し、termination reason が記録されます:

- `max_depth_exceeded`
- `max_steps_exceeded`
- `cycle_detected`

## Allowlist

Supervisorごとに許可ターゲットを制限できます。

```python
supervisor_allowlists = {"domain": {"fashion", "done"}}
```

注意点:
- allowlistには `call_subgraph::` を付けず **subgraph_id** (`fashion`) を指定します。
- allowlist違反時は `response_type="terminal"` で停止し、
  `termination_reason="allowlist_violation"` が decision trace に残ります。

## DecisionTrace

`enable_subgraphs=True` のとき、ルーティング履歴が
`_internal.decision_trace` に記録されます。

主なフィールド:
- `step`: グローバルのステップ数
- `depth`: call stack の深さ
- `supervisor`: supervisor名
- `decision_kind`: `NODE`, `SUBGRAPH`, `STOP_LOCAL`, `STOP_GLOBAL`, `FALLBACK`
- `target`: 選択されたノード名やsubgraph_id
- `termination_reason`: 安全停止時のみ

## 互換性 (legacy)

ヒエラリカル構造は **opt-in** で、`_internal.decision` には従来通り文字列が入ります。
既存のフラットなグラフは変更なしで動作します。
