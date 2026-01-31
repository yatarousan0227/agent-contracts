# v0.6.0: ヒエラリカル構造（Subgraph呼び出し）対応 — PR04（Validator: 境界/allowlist/strict）

## 目的
- Subgraph境界（reads/writes）と参照整合性を **静的に** 検証し、実行前に事故を止める。
- 既存利用への影響を避けるため、Subgraphを使う場合のみ検証を強める（または `strict=True`）。

## スコープ
- `ContractValidator` に Subgraph関連の検証を追加
- strict/non-strict の挙動をテストで固定

## 追加する検証（案）
### 1) Subgraph boundary
- Subgraphに含まれる各nodeについて:
  - `NodeContract.reads ⊆ SubgraphContract.reads`
  - `NodeContract.writes ⊆ SubgraphContract.writes`

### 2) Subgraph定義の整合性
- `SubgraphContract.entrypoint` が存在する（node/supervisorとして解決可能）
- SubgraphDefinitionで列挙した supervisor/node が registry 上に存在する

### 3) allowlist整合性
- allowlistに存在しない node/subgraph_id が含まれていない

### 4) strictモード
- `strict=False`:
  - 破壊的なものだけ error、それ以外は warning（PR00の方針に合わせる）
- `strict=True`:
  - warning→error 昇格（既存の仕組みを踏襲）

## 対象ファイル
- `src/agent_contracts/validator.py`
- `tests/test_validator.py`（追加）

## テストケース
- boundary違反で error（strict関係なく）
- entrypoint不在/参照不整合で error
- allowlist不整合で warning or error（方針に従い固定）
- strictでwarningがerrorに昇格する

## 受け入れ条件
- 既存グラフのみのプロジェクトでvalidatorが壊れない
- Subgraphを使う場合の静的事故検知がテストで担保されている

