# v0.6.0: ヒエラリカル構造（Subgraph呼び出し）対応 — PR02（Registry: Subgraph登録/解決）

## 目的
- `NodeRegistry` に Subgraph を登録・参照できる仕組みを追加する。
- node名との衝突や存在しない参照を早期に検知できるようにする。

## スコープ
- `NodeRegistry` の拡張（後方互換）
- Subgraphのexport（Visualizer/Validatorで使う）
- 単体テスト

## 追加API（案）
- `NodeRegistry.register_subgraph(contract: SubgraphContract, definition: SubgraphDefinition) -> None`
- `NodeRegistry.get_subgraph(subgraph_id: str) -> tuple[SubgraphContract, SubgraphDefinition] | None`
- `NodeRegistry.list_subgraphs() -> list[str]`
- `NodeRegistry.export_subgraphs() -> dict[str, dict]`（CLI/Visualizer向け）

## 衝突/整合性ルール（このPRで実装）
- `subgraph_id` が既存 node 名（`NodeContract.name`）と衝突する場合はエラー
- 同じ `subgraph_id` の再登録はエラー
- 予約プレフィックス `call_subgraph::` はユーザー定義node名として使わない（衝突した場合はエラー/警告にする方針を後続PRで実装）

## 対象ファイル
- `src/agent_contracts/registry.py`
- `tests/test_registry.py`（追記 or 新規 `tests/test_subgraphs_registry.py`）

## テストケース
- register/get/list が期待通り
- node名衝突で例外
- duplicate subgraph_id で例外

## 受け入れ条件
- Subgraphを登録しない既存利用は無影響
- Subgraph登録の基本操作がテストで担保されている
