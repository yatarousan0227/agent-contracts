# v0.6.0: ヒエラリカル構造（Subgraph呼び出し）対応 — PR00（ADR/Spec）

## 目的
- v0.6.0で導入する「階層Subgraph（親Supervisor→子Subgraph→復帰 / 再帰）」の仕様を固定し、後続PRの実装ブレを無くす。
- **非破壊・opt-in** を明文化し、既存のフラットグラフが無変更で動くことを保証する。

## スコープ（このPRでやること）
- ドキュメント追加のみ（実装の挙動変更なし）。
- 既存の `agent_contracts.routing.RoutingDecision` と名称衝突しない設計を確定。

## 主要な設計決定（Freeze）
### 1) 「Subgraph呼び出し」の表現
- LangGraph内では、Subgraphを **「呼び出し用ノード（CallSubgraphノード）」** として表現する。
  - 既存のGraphBuilder/条件分岐（`_internal.decision` が文字列）と整合するため。
  - 既存Supervisor/Routerが `str` を返す世界観を維持しつつ、Subgraph呼び出しも同じルーティング機構で扱える。

### 2) 互換性（Must）
- Subgraphを登録しない場合、既存の `NodeRegistry` / `GraphBuilder` / `GenericSupervisor` の挙動は変えない。
- Supervisorの出力は引き続き **`str` を許容**（legacy互換）。
  - （opt-in）で新しい意思決定型（例: `HierarchicalDecision`）を追加しても良いが、必須化しない。

### 3) Stateの追加キー（置き場所）
- 追加情報は `"_internal"` 配下に格納し、既存stateに必須フィールドを増やさない。
- 追加キー案（確定すること）:
  - `"_internal.call_stack"`: list[frame]
  - `"_internal.budgets"`: budgets
  - `"_internal.decision_trace"`: list[item]
  - `"_internal.visited_subgraphs"`: dict[subgraph_id, count]
  - `"_internal.step_count"`: int（node/supervisor wrapperで増加）

### 4) STOPの意味（Subgraph内終了/全体終了）
- **STOP_LOCAL**: Subgraphの実行を終了し、親に復帰する（CallSubgraphノードが return する）。
  - 実装上は「子graphが `END` に到達＝STOP_LOCAL」とみなす。
- **STOP_GLOBAL**: セッション全体を終了する。
  - 実装上は既存の仕組み（`response.response_type` が terminal）を利用し、親に復帰後のroutingで終了させる。

### 5) 安全装置（再帰）
- budgets（デフォルト）:
  - `max_depth=2`
  - `max_steps=40`
  - `max_reentry=2`
- enforcement（固定すること）:
  - `max_depth` 超過: 安全停止（terminal）+ `termination_reason="max_depth_exceeded"`
  - `max_steps` 超過: 安全停止（terminal）+ `termination_reason="max_steps_exceeded"`
  - `max_reentry` 超過（cycle/再入）: 安全停止（terminal）+ `termination_reason="cycle_detected"`

### 6) allowlist違反時の挙動
- Supervisorが許可されていない node/subgraph を選んだ場合の挙動を固定する。
  - 推奨: **安全停止（terminal）** し、`termination_reason="allowlist_violation"` をtraceに記録。
  - 代替: fallbackノードに強制ルーティング（ただしプロジェクト依存が強いのでv0.6.0では非推奨）

## 変更/追加するファイル（案）
- `docs/spec/hierarchical-supervisor-v0.6.0.md`
- `docs/adr/ADR-xxx-hierarchical-supervisor-v0.6.0.md`

## 受け入れ条件
- docsに「状態キー」「STOP」「budgets」「allowlist違反時挙動」が明記されている
- 後続PRが参照すべき“固定仕様”が一箇所にまとまっている

