# API Reference (Public)

本ドキュメントは `agent_contracts` のPublic APIを、
「目的 → 署名 → 最小例 → 主要引数/戻り値 → 注意点」のテンプレで整理したものです。

---

## Core Types

### __version__
- **目的**: ライブラリのバージョン文字列を取得する。
- **署名**: `__version__: str`
- **最小例**:
  ```python
  import agent_contracts as ac
  print(ac.__version__)
  ```
- **主要引数/戻り値**: 戻り値はバージョン文字列。
- **注意点**: 互換性判断のために利用できるが、実装詳細とは独立。 

### NodeContract
- **目的**: ノードのI/O・依存・トリガーを宣言する契約オブジェクト。
- **署名**: `NodeContract(name: str, description: str, reads: list[str], writes: list[str], requires_llm: bool = False, services: list[str] = [], supervisor: str, trigger_conditions: list[TriggerCondition] = [], is_terminal: bool = False, icon: str | None = None)`
- **最小例**:
  ```python
  from agent_contracts import NodeContract, TriggerCondition

  CONTRACT = NodeContract(
      name="search",
      description="Search knowledge base",
      reads=["request"],
      writes=["response"],
      supervisor="main",
      trigger_conditions=[TriggerCondition(when={"request.action": "search"})],
  )
  ```
- **主要引数/戻り値**: `reads/writes` が参照・更新するスライス、`trigger_conditions` が起動条件。
- **注意点**: `requires_llm=True` の場合はノード初期化時にLLMを注入する。 

### TriggerCondition
- **目的**: ノードを起動する条件（ルール/LLMヒント）を表現する。
- **署名**: `TriggerCondition(priority: int = 0, when: dict[str, Any] | None = None, when_not: dict[str, Any] | None = None, llm_hint: str | None = None)`
- **最小例**:
  ```python
  from agent_contracts import TriggerCondition

  condition = TriggerCondition(
      priority=100,
      when={"request.action": "search"},
      llm_hint="Search when action is search",
  )
  ```
- **主要引数/戻り値**: `when`/`when_not` が状態マッチ条件、`priority` が優先度。
- **注意点**: `when` と `when_not` の両方指定も可能（両方を満たす必要あり）。 

### NodeInputs
- **目的**: ノードが読むスライスを保持する入力コンテナ。
- **署名**: `NodeInputs(**slices)`
- **最小例**:
  ```python
  async def execute(self, inputs):
      req = inputs.get_slice("request")
  ```
- **主要引数/戻り値**: `get_slice(name)` が辞書スライスを返す。
- **注意点**: 契約外のスライス参照は設定により警告/例外となる。 

### NodeOutputs
- **目的**: ノードが更新するスライスを保持する出力コンテナ。
- **署名**: `NodeOutputs(**slices)`
- **最小例**:
  ```python
  from agent_contracts import NodeOutputs

  return NodeOutputs(response={"response_type": "done"})
  ```
- **主要引数/戻り値**: `to_state_updates()` がLangGraph向け更新辞書を返す。
- **注意点**: `None` の値は更新辞書から除外される。 

### ModularNode
- **目的**: すべてのノードの基底クラス。契約に基づくI/O検証と実行フローを提供する。
- **署名**: `class ModularNode(ABC)` / `__init__(llm: BaseChatModel | None = None, **services)` / `execute(inputs: NodeInputs, config: RunnableConfig | None = None) -> NodeOutputs`
- **最小例**:
  ```python
  from agent_contracts import ModularNode, NodeOutputs

  class MyNode(ModularNode):
      CONTRACT = ...
      async def execute(self, inputs, config=None):
          return NodeOutputs(response={"response_type": "done"})
  ```
- **主要引数/戻り値**: `execute` が実処理、`__call__` がLangGraph互換エントリ。
- **注意点**: `CONTRACT` に `requires_llm=True` がある場合、`llm` を渡す。 

### InteractiveNode
- **目的**: 対話フロー向けの標準実行ステップ（準備→回答処理→完了判定→次質問）を提供する。
- **署名**: `class InteractiveNode(ModularNode)` / `prepare_context(...)` / `process_answer(...)` / `check_completion(...)` / `generate_question(...)`
- **最小例**:
  ```python
  class InterviewNode(InteractiveNode):
      CONTRACT = ...
      def prepare_context(self, inputs):
          return {}
      def check_completion(self, context, inputs):
          return False
      async def process_answer(self, context, inputs, config=None):
          return False
      async def generate_question(self, context, inputs, config=None):
          return NodeOutputs(response={"response_type": "question"})
  ```
- **主要引数/戻り値**: `execute` は抽象メソッド群を順に呼ぶ。
- **注意点**: `process_answer` は `bool` を返すが状態更新は自前で行う。 

### BaseRequestSlice / BaseResponseSlice / BaseInternalSlice
- **目的**: 代表的な状態スライスのTypedDictテンプレート。
- **署名**:
  - `class BaseRequestSlice(TypedDict, total=False)`
  - `class BaseResponseSlice(TypedDict, total=False)`
  - `class BaseInternalSlice(TypedDict, total=False)`
- **最小例**:
  ```python
  from agent_contracts import BaseRequestSlice

  req: BaseRequestSlice = {"session_id": "s1", "action": "ask"}
  ```
- **主要引数/戻り値**: 型ヒント用途。
- **注意点**: 実運用ではプロジェクト固有のスライスを拡張して使用。 

### BaseAgentState
- **目的**: `request/response/_internal` を含む最小状態構造のTypedDict。
- **署名**: `class BaseAgentState(TypedDict, total=False)`
- **最小例**:
  ```python
  class MyState(BaseAgentState):
      user: dict
  ```
- **主要引数/戻り値**: 型ヒント用途。
- **注意点**: スライス追加は継承で行う。 

### get_slice
- **目的**: 状態からスライス辞書を安全に取得する。
- **署名**: `get_slice(state: dict, slice_name: str) -> dict`
- **最小例**:
  ```python
  from agent_contracts import get_slice

  request = get_slice(state, "request")
  ```
- **主要引数/戻り値**: 戻り値は辞書（存在しない場合は空辞書）。
- **注意点**: 型安全性は保証しない。 

### merge_slice_updates
- **目的**: LangGraph向けのスライス更新をマージする。
- **署名**: `merge_slice_updates(state: dict, updates: dict[str, Any] | None) -> dict[str, Any]`
- **最小例**:
  ```python
  updates = merge_slice_updates(state, {"response": {"response_type": "done"}})
  ```
- **主要引数/戻り値**: `updates` に既存スライスを統合して返す。
- **注意点**: `updates` が `None` の場合は空辞書を返す。 

### StateAccessor
- **目的**: 状態のフィールドに対して型安全なget/setを提供する。
- **署名**: `StateAccessor(slice_name: str, field_name: str, default: T)`
- **最小例**:
  ```python
  from agent_contracts import StateAccessor

  count = StateAccessor("_internal", "turn_count", 0)
  value = count.get(state)
  state = count.set(state, value + 1)
  ```
- **主要引数/戻り値**: `get(state) -> T` / `set(state, value) -> dict`
- **注意点**: 変更は常に新しい辞書を返す（イミュータブル）。 

### Internal / Request / Response
- **目的**: 標準スライスのアクセサー集。
- **署名**:
  - `class Internal`
  - `class Request`
  - `class Response`
- **最小例**:
  ```python
  from agent_contracts import Internal, Request

  turn = Internal.turn_count.get(state)
  action = Request.action.get(state)
  ```
- **主要引数/戻り値**: 各フィールドは `StateAccessor`。
- **注意点**: `Internal` は原則ノードから直接操作しない。 

### reset_response / increment_turn / set_error / clear_error
- **目的**: 状態スライスの便利操作。
- **署名**:
  - `reset_response(state: dict) -> dict`
  - `increment_turn(state: dict) -> dict`
  - `set_error(state: dict, error: str) -> dict`
  - `clear_error(state: dict) -> dict`
- **最小例**:
  ```python
  state = increment_turn(state)
  state = set_error(state, "invalid")
  ```
- **主要引数/戻り値**: いずれも新しい状態辞書を返す。
- **注意点**: すべてイミュータブル操作。 

### RoutingDecision / RoutingReason / MatchedRule
- **目的**: ルーティングの根拠を構造化して保持する型。
- **署名**:
  - `RoutingDecision(selected_node: str, reason: RoutingReason)`
  - `RoutingReason(decision_type: str, matched_rules: list[MatchedRule] = [], llm_used: bool = False, llm_reasoning: str | None = None)`
  - `MatchedRule(node: str, condition: str, priority: int)`
- **最小例**:
  ```python
  decision = await supervisor.decide_with_trace(state)
  print(decision.selected_node)
  ```
- **主要引数/戻り値**: `RoutingDecision.to_supervisor_decision()` で簡易形式に変換可能。
- **注意点**: `decision_type` は `terminal_state/rule_match/llm_decision` などを想定。 

### SupervisorDecision
- **目的**: Supervisorの最終決定を簡易に表す型。
- **署名**: `SupervisorDecision(next_node: str, reasoning: str = "")`
- **最小例**:
  ```python
  decision = await supervisor.decide(state)
  print(decision.next_node)
  ```
- **主要引数/戻り値**: `next_node` が次に実行するノード名。
- **注意点**: 詳細な理由が必要なら `decide_with_trace` を使用。 

### BaseActionRouter
- **目的**: actionベースのルーティングを実装する抽象基底。
- **署名**: `class BaseActionRouter(ABC)` / `route(action: str, state: dict | None = None) -> str`
- **最小例**:
  ```python
  class MyRouter(BaseActionRouter):
      def route(self, action, state=None):
          return "default_supervisor"
  ```
- **主要引数/戻り値**: `__call__(state)` でLangGraphノードとして利用可能。
- **注意点**: `route` が `ValueError` を投げるとエラー応答を作成する。 

### ContractValidator / ValidationResult
- **目的**: 登録済み契約の静的検証を行う。
- **署名**:
  - `ContractValidator(registry: NodeRegistry, known_services: set[str] | None = None, strict: bool = False)`
  - `ValidationResult(errors: list[str] = [], warnings: list[str] = [], info: list[str] = [])`
- **最小例**:
  ```python
  validator = ContractValidator(get_node_registry())
  result = validator.validate()
  print(result)
  ```
- **主要引数/戻り値**: `validate() -> ValidationResult`。
- **注意点**: `strict=True` で警告もエラー扱いにできる。 

### ContractVisualizer
- **目的**: NodeRegistryからアーキテクチャドキュメントを生成する。
- **署名**: `ContractVisualizer(registry: NodeRegistry, graph: CompiledStateGraph | None = None)`
- **最小例**:
  ```python
  visualizer = ContractVisualizer(get_node_registry())
  markdown = visualizer.generate_architecture_doc()
  ```
- **主要引数/戻り値**: `generate_architecture_doc() -> str`。
- **注意点**: `graph` を渡すとLangGraphフローのMermaidを含められる。 

### ContractDiffReport / NodeChange / diff_contracts
- **目的**: 2つの契約セットの差分を構造化して取得する。
- **署名**:
  - `ContractDiffReport(added: list[str], removed: list[str], changes: list[NodeChange])`
  - `NodeChange(node: str, severity: str, details: list[str] = [])`
  - `diff_contracts(before: dict[str, dict], after: dict[str, dict]) -> ContractDiffReport`
- **最小例**:
  ```python
  before = registry.export_contracts()
  # ... registry update ...
  after = registry.export_contracts()
  report = diff_contracts(before, after)
  print(report.to_text())
  ```
- **主要引数/戻り値**: `ContractDiffReport.has_breaking()` で破壊的変更を判定。
- **注意点**: `before/after` は `NodeContract.model_dump()` 形式を想定。 

### ContractViolationError
- **目的**: 契約違反（宣言外I/Oなど）を表す例外。
- **署名**: `class ContractViolationError(RuntimeError)`
- **最小例**:
  ```python
  try:
      outputs = await node(state)
  except ContractViolationError:
      ...
  ```
- **主要引数/戻り値**: 例外クラス。
- **注意点**: 厳格モードでI/O違反が例外化される。 

---

## Registry & Build

### NodeRegistry
- **目的**: ノード登録・契約管理・トリガー評価を行うレジストリ。
- **署名**: `NodeRegistry(valid_slices: set[str] | None = None)`
- **最小例**:
  ```python
  registry = NodeRegistry()
  registry.register(MyNode)
  matches = registry.evaluate_triggers("main", state)
  ```
- **主要引数/戻り値**: `register(node_class)` / `evaluate_triggers(supervisor, state)`。
- **注意点**: `valid_slices` に含まれないスライス名は警告対象。 

### TriggerMatch
- **目的**: トリガー条件が一致した結果を表すデータ型。
- **署名**: `TriggerMatch(priority: int, node_name: str, condition_index: int)`
- **最小例**:
  ```python
  matches = registry.evaluate_triggers("main", state)
  top = matches[0]
  ```
- **主要引数/戻り値**: `priority` が高い順にソートされる。
- **注意点**: `condition_index` は `trigger_conditions` 配列のインデックス。 

### get_node_registry / reset_registry
- **目的**: グローバルなNodeRegistryを取得/リセットする。
- **署名**:
  - `get_node_registry() -> NodeRegistry`
  - `reset_registry() -> None`
- **最小例**:
  ```python
  registry = get_node_registry()
  reset_registry()
  ```
- **主要引数/戻り値**: なし。
- **注意点**: テスト用途で `reset_registry` を使うと安全。 

### GenericSupervisor
- **目的**: トリガー条件＋LLMで次ノードを決定する汎用Supervisor。
- **署名**: `GenericSupervisor(supervisor_name: str, llm: BaseChatModel | None = None, registry: NodeRegistry | None = None, max_iterations: int | None = None, terminal_response_types: set[str] | None = None, context_builder: ContextBuilder | None = None, max_field_length: int | None = None, explicit_routing_handler: ExplicitRoutingHandler | None = None)`
- **最小例**:
  ```python
  supervisor = GenericSupervisor("main", llm=llm)
  decision = await supervisor.decide(state)
  ```
- **主要引数/戻り値**: `decide(state)` / `decide_with_trace(state)` / `run(state)`。
- **注意点**: `decide_with_trace` は `RoutingDecision` を返す。 

### GraphBuilder
- **目的**: NodeRegistryからLangGraphを構築するビルダー。
- **署名**: `GraphBuilder(registry: NodeRegistry | None = None, state_class: type | None = None, llm_provider: Callable[[], Any] | None = None, dependency_provider: Callable[[NodeContract], dict] | None = None, supervisor_factory: Callable[[str, Any], GenericSupervisor] | None = None)`
- **最小例**:
  ```python
  builder = GraphBuilder(get_node_registry())
  builder.add_supervisor("main", llm=llm)
  # builder.create_node_wrapper(...) などを使って StateGraph を組み立てる
  ```
- **主要引数/戻り値**: `add_supervisor(name, llm, **services)` / `create_node_wrapper(...)` / `create_supervisor_wrapper(...)`。
- **注意点**: `llm_provider` を使うとノードごとにLLMを生成できる。 

### build_graph_from_registry
- **目的**: レジストリからLangGraphを一括生成するユーティリティ。
- **署名**: `build_graph_from_registry(registry: NodeRegistry | None = None, llm=None, llm_provider: Callable[[], Any] | None = None, dependency_provider: Callable[[NodeContract], dict] | None = None, supervisor_factory: Callable[[str, Any], GenericSupervisor] | None = None, entrypoint: tuple[str, Callable, Callable] | None = None, supervisors: list[str] | None = None, state_class: type | None = None, **services) -> StateGraph`
- **最小例**:
  ```python
  graph = build_graph_from_registry(get_node_registry(), llm=llm, supervisors=["main"])
  compiled = graph.compile()
  ```
- **主要引数/戻り値**: 戻り値はコンパイル前の `StateGraph`。
- **注意点**: `entrypoint` を指定すると外部ルーターを起点にできる。 

---

## Runtime

### RequestContext
- **目的**: 実行リクエストの情報を保持するデータクラス。
- **署名**: `RequestContext(session_id: str, action: str, params: dict[str, Any] | None = None, message: str | None = None, image: str | None = None, resume_session: bool = False, metadata: dict[str, Any] = {})`
- **最小例**:
  ```python
  from agent_contracts import RequestContext

  ctx = RequestContext(session_id="s1", action="answer", message="hi")
  ```
- **主要引数/戻り値**: `get_param(key, default)` でparams取得。
- **注意点**: `resume_session=True` でセッション復元を試みる。 

### ExecutionResult
- **目的**: 実行結果（最終状態とレスポンス）を保持するデータクラス。
- **署名**: `ExecutionResult(state: dict[str, Any], response_type: str | None = None, response_data: dict[str, Any] | None = None, response_message: str | None = None, success: bool = True, error: str | None = None)`
- **最小例**:
  ```python
  result = await runtime.execute(ctx)
  print(result.response_type)
  ```
- **主要引数/戻り値**: `from_state(state)` / `error_result(error, state=None)` / `to_response_dict()`。
- **注意点**: `to_response_dict()` は `response_type` を優先して `type` に反映。 

### RuntimeHooks / DefaultHooks
- **目的**: 実行ライフサイクルのフックを提供するプロトコル／デフォルト実装。
- **署名**:
  - `RuntimeHooks.prepare_state(state: dict, request: RequestContext) -> dict`
  - `RuntimeHooks.after_execution(state: dict, result: ExecutionResult) -> None`
  - `class DefaultHooks`
- **最小例**:
  ```python
  class MyHooks:
      async def prepare_state(self, state, request):
          return state
      async def after_execution(self, state, result):
          pass
  ```
- **主要引数/戻り値**: `prepare_state` は状態辞書を返す。
- **注意点**: 変更はイミュータブルに行うこと。 

### SessionStore / InMemorySessionStore
- **目的**: セッションの永続化を抽象化する。
- **署名**:
  - `SessionStore.load(session_id: str) -> dict | None`
  - `SessionStore.save(session_id: str, data: dict, ttl_seconds: int = 3600) -> None`
  - `SessionStore.delete(session_id: str) -> None`
  - `InMemorySessionStore()`
- **最小例**:
  ```python
  store = InMemorySessionStore()
  await store.save("s1", {"_internal": {"turn_count": 1}})
  ```
- **主要引数/戻り値**: `load` はセッション辞書または `None`。
- **注意点**: `InMemorySessionStore` は開発/テスト用途専用。 

### AgentRuntime
- **目的**: グラフの実行・状態初期化・セッション復元・フック適用を統合したランタイム。
- **署名**: `AgentRuntime(graph: Any, hooks: RuntimeHooks | None = None, session_store: SessionStore | None = None, slices_to_restore: list[str] | None = None)`
- **最小例**:
  ```python
  runtime = AgentRuntime(compiled_graph, session_store=InMemorySessionStore())
  result = await runtime.execute(RequestContext(session_id="s1", action="ask"))
  ```
- **主要引数/戻り値**: `execute(request: RequestContext) -> ExecutionResult`。
- **注意点**: 例外は `ExecutionResult.error_result(...)` に変換される。 
