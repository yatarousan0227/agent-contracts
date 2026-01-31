# v0.6.0: ヒエラリカル構造（Subgraph呼び出し）対応 — PR05（Visualizer: Subgraphクラスタ + Call edge）

## 目的
- Subgraph階層を可視化し、親→子の呼び出し関係をドキュメントに反映する。
- Subgraph未使用時の既存出力は変えない（安定性）。

## スコープ
- Mermaidの階層図に Subgraphクラスタを導入
- `call_subgraph::<id>` ノードと呼び出しエッジを表現

## 実装方針（案）
- `NodeRegistry.export_subgraphs()` の情報を利用し、以下を生成:
  - `subgraph <id> [...] end` ブロック（Mermaidのsubgraph）
  - 親Supervisor → `call_subgraph::<id>` の点線エッジ
  - `call_subgraph::<id>` → 子entrypoint への注釈付きエッジ（可能なら）

## 対象ファイル
- `src/agent_contracts/visualizer.py`
- `tests/test_visualizer.py`（スナップショット/文字列比較追加）

## テスト
- Subgraph無し: 既存出力が変わらない（既存テストで担保）
- Subgraph有り: クラスタとcall edgeが含まれる

## 受け入れ条件
- `agent-contracts visualize ...` の出力で階層が追える
- Subgraph未使用プロジェクトの出力が安定

