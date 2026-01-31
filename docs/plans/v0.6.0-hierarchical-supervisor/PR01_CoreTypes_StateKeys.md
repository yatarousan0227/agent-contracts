# v0.6.0: ヒエラリカル構造（Subgraph呼び出し）対応 — PR01（コア型/Stateキー）

## 目的
- Subgraph登録・呼び出し・観測性・安全装置に必要な **コア型** を追加し、後続PRの実装を安定させる。
- `"_internal"` の追加キーを「型/アクセサ/ドキュメント」として整備する（実行ロジックはPR03で）。

## スコープ
- 新規クラス/モデル（pydantic/dataclass）追加
- `state.py` / `state_accessors.py` への **後方互換な** 拡張
- public export整備
- 単体テスト追加

## 追加する型（案）
### Subgraph定義
- `SubgraphContract`
  - `subgraph_id: str`
  - `description: str`
  - `reads: list[str]`
  - `writes: list[str]`
  - `entrypoint: str`（subgraph内の開始ノード名 or supervisor名）
  - `input_schema: type[BaseModel] | None`（任意）
  - `output_schema: type[BaseModel] | None`（任意）
- `SubgraphDefinition`
  - `subgraph_id: str`
  - `supervisors: list[str]` / `nodes: list[str]`（どちらか一方、または解決ルール）

### 実行時データ
- `Budgets`
  - `max_depth: int`
  - `max_steps: int`
  - `max_reentry: int`
- `CallStackFrame`
  - `subgraph_id: str`
  - `depth: int`
  - `entry_step: int`
  - `locals: dict`（subgraph inputなど）
- `DecisionTraceItem`
  - `step: int`
  - `depth: int`
  - `supervisor: str | None`
  - `decision_kind: str`（"NODE"/"SUBGRAPH"/"STOP_LOCAL"/"STOP_GLOBAL"/"FALLBACK"）
  - `target: str | None`
  - `reason: str | None`
  - `termination_reason: str | None`

### 命名（重要）
- 既存に `agent_contracts.routing.RoutingDecision` が存在するため、階層実行の意思決定型は別名にする。
  - 例: `HierarchicalDecision` / `ExecutionDecision`

## 対象ファイル（案）
- `src/agent_contracts/subgraph.py`（新規）
- `src/agent_contracts/runtime/hierarchy.py`（新規: budgets/callstack/trace）
- `src/agent_contracts/state.py`（`BaseInternalSlice` に任意キー追加）
- `src/agent_contracts/state_accessors.py`（`Internal` に accessors 追加）
- `src/agent_contracts/__init__.py`（export追加）
- `src/agent_contracts/runtime/__init__.py`（export追加）

## テスト（案）
- `tests/test_subgraph_types.py`（新規）
  - SubgraphContract/Budgets/CallStackFrame/DecisionTraceItem の生成・シリアライズ
- `tests/test_state_accessors.py` 追記
  - 新アクセサが `"_internal"` に安全に set/get できる

## 受け入れ条件
- コア型が import 可能で、最低限のテストが通る
- `state.py` の変更が後方互換（既存stateでも動作）である

