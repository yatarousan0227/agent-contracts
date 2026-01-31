# v0.6.0: ヒエラリカル構造（Subgraph呼び出し）対応 — PR03（GraphBuilder: CallSubgraphノード + budgets/trace）

## 目的
- LangGraphの「1つのグラフ」内で、Subgraphを **呼び出し用ノード** として実行できるようにする。
- 再帰/循環の安全装置（budgets/cycle）と観測性（trace/call_stack）を実装する。
- 既存 `AgentRuntime` を置き換えずに階層化を成立させる（非破壊）。

## 実装方針（既存設計に合わせる）
### CallSubgraphは「ノード」として追加
- 親Supervisorが選ぶのは `call_subgraph::<subgraph_id>` のような **node名文字列**。
- GraphBuilderが Subgraph登録を見て、該当する CallSubgraphノードを `StateGraph` に追加する。

### step_countの導入（max_stepsのため）
- `GraphBuilder.create_node_wrapper` / `create_supervisor_wrapper` の wrapper 内で
  - `"_internal.step_count"` を +1
  - `"_internal.decision_trace"` に最低限のイベントを追記（可能なら）

## 追加/変更点（案）
### 1) GraphBuilderの拡張
- `build_graph_from_registry(..., enable_subgraphs: bool = False)` のようなopt-inを追加
  - `False` のとき既存挙動を維持
- Subgraphごとに CallSubgraphノードを自動追加
  - ノード名規約: `call_subgraph::<subgraph_id>`（固定）
  - 既存node名との衝突（ユーザーが同名nodeを定義している等）は **起動時にエラー** にする（予約プレフィックス）
  - 返り先: 呼び出し元Supervisor（既存の「worker→supervisor」エッジで復帰）

### 2) Subgraphのコンパイル/実行
- CallSubgraphノード内で、対象Subgraph用に **別のStateGraph** を構築して `compile()` し、`ainvoke(state)` する
  - compiled graph のキャッシュ（subgraph_id→compiled）を入れて再利用
- Subgraph内で `END` に到達したら STOP_LOCAL とみなして親へ復帰

### 3) budgets / cycle detection（状態キーはPR00準拠）
- 呼び出し前に:
  - `call_stack` push（depth算出）
  - `visited_subgraphs[subgraph_id] += 1`
  - `step_count` / `depth` / `visited` を用いて停止判定
- 停止する場合は:
  - `response.response_type` を terminal に設定（既存の終了機構を利用）
  - `decision_trace` に `termination_reason` を記録
  - 親に復帰後、routingで `END` に到達させる

### 4) allowlist enforcement（実行時）
- Supervisorに allowlist が設定されている場合:
  - `"_internal.decision"` が許可されていない（node/subgraph）なら安全停止（推奨）
  - `termination_reason="allowlist_violation"` を trace に記録

## 対象ファイル（案）
- `src/agent_contracts/graph_builder.py`
- `src/agent_contracts/supervisor.py`（allowlistを受け取る拡張をする場合）
- `src/agent_contracts/runtime/state_ops.py`（必要なら内部state操作ユーティリティ）
- `tests/test_graph_builder.py`（統合寄りのテスト追加）
- `tests/test_runtime.py`（E2E寄りのテスト追加）

## 追加テスト（最小E2E）
- 親Supervisor → `call_subgraph::fashion` → 子Supervisor → 子node → END → 親に復帰 → 継続/終了
- `max_depth` 超過で安全停止 + traceに理由
- cycle（同一subgraph再入）で `max_reentry` 超過停止
- `max_steps` 超過停止（wrapperでstep_countを増やす）

## 受け入れ条件
- Subgraph未使用時のグラフ生成/実行が無影響（既存テストが通る）
- Subgraph呼び出しが実際に動く最小統合テストが通る
- budgets/cycle/allowlist違反が安全に止まり、traceが残る
