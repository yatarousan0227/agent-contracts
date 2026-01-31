# v0.6.0: ヒエラリカル構造（Subgraph呼び出し）対応 — PR06（Examples/Docs/Release）

## 目的
- ユーザーが最小構成でSubgraphを試せる例と、移行ガイドを提供する。
- v0.6.0としてリリース可能な状態にまとめる（changelog/version）。

## スコープ
- example追加（CIで動く軽量なもの）
- ドキュメント追加（使い方/概念/制約）
- `CHANGELOG.md` / `pyproject.toml` のバージョン更新

## Examples（案）
- `examples/hierarchical_supervisor_minimal/`
  - 親Supervisor: `DomainSupervisor`
  - Subgraph: `fashion`
  - 子Supervisor: `FashionSupervisor`
  - 子node: `TrendNode`
  - 親に復帰して終了（または続行）
- 追加で「安全停止」デモ（max_depth/cycle）も入れる（任意）

## ドキュメント（案）
- `docs/guides/hierarchical-supervisor.md`（英語）
- `docs/guides/hierarchical-supervisor.ja.md`（日本語）
  - STOP_LOCAL/STOP_GLOBAL（実装上の表現）
  - budgets/cycle detection（設定方法とデフォルト）
  - allowlist（違反時挙動）
  - DecisionTraceの読み方（stateのどこに入るか）
  - legacy（str decision）の互換性

## リリース作業
- `CHANGELOG.md` に追加（Breaking無し / opt-in）
- `pyproject.toml` を `0.6.0` に更新

## 受け入れ条件
- exampleがREADME通りに動く（pytest等で最低限検証）
- docsが「何をどう使うか」を説明できている
- version/changelogが整合している

