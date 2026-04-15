# システムアーキテクチャ

## プロジェクト概要

AI-Consumer-Persona（Digital Twin）は、LLM を活用して **生活者** の AI ペルソナを
構築し、プロモーション反応や購買意向をシミュレーションするシステムである。

[医師版 AI-persona](https://github.com/OM35156/AI-persona) から派生しており、
RAG 基盤・ABM・評価メトリクス等の汎用モジュールを継承しつつ、生活者ドメインに特化した
スキーマ・プロンプト・評価を備える。

## ディレクトリ構成

```
AI-consumer-persona/
├── src/digital_twin/        ← メインソースコード
│   ├── abm/                 ← エージェントベースモデル（採用/影響伝播）
│   ├── api/                 ← API エンドポイント（FastAPI）
│   ├── data/                ← データ読込・スキーマ・匿名化
│   ├── engine/              ← シミュレーションエンジン（プロンプト・実行）
│   ├── evaluation/          ← 評価（メトリクス・バリデーション・可視化）
│   ├── persona/             ← ペルソナ構築・プロファイル管理
│   ├── pretest/             ← プレテスト・ポテンシャルモデル
│   ├── rag/                 ← ベクトルDB検索・セグメントプロファイル
│   ├── ui/                  ← Streamlit UI
│   └── utils/               ← 設定読込・コスト計算
├── configs/                 ← 設定ファイル（base.yaml, poc.yaml）
├── data/                    ← データ格納（dummy/raw/processed/synthetic）
├── scripts/                 ← 実行スクリプト（etl, ingest, synth）
├── templates/               ← プロンプトテンプレート
├── tests/                   ← テスト（unit/integration/fixtures）
└── ai_docs/                 ← AI 向けドキュメント
```

## 主要モジュール

### data（データ層）
- `loader.py` — データ読込
- `schema.py` — 生活者データスキーマ定義（Consumer / ConsumerDemographics /
  CategoryProfile / BrandExposure 等、Pydantic v2）
- `anonymizer.py` — 匿名化処理（k-匿名性・セル抑制）

### persona（ペルソナ層）
- `builder.py` — 生活者ペルソナ構築ロジック（`ConsumerPersonaBuilder`）
- `profile.py` — 生活者ペルソナ定義（`ConsumerPersona`）。Persona Strategy 書籍の
  設計思想（Identification / Goals / Factoids / Psychological Details）に準拠

### engine（シミュレーション層）
- `prompt.py` — LLM プロンプト生成（層①セグメントプロファイル + 層②RAG コンテキスト）
- `simulator.py` — シミュレーション実行（Claude API 呼び出し、リトライ、コストトラッキング）

### evaluation（評価層）
- `metrics.py` — 評価メトリクス（JS divergence 等の分布差検定）
- `validator.py` — 結果バリデーション
- `visualization.py` — 結果可視化

### rag（RAG 層）
- `context_builder.py` — セグメントプロファイル + ベクトルDB 検索結果から確信度ラベル
  （[データ根拠あり] / [推論] / [データ外]）付きコンテキストを構築
- `embedder.py`, `search_client.py` — 埋め込み生成とベクトルDB アクセス

### abm（エージェントベースモデル層）
- `consumer_agent.py`（※#3 でリネーム予定）— 採用状態遷移（AdoptionState）を持つ
  生活者エージェント
- `model.py` — ネットワーク上での影響伝播シミュレーション
- `network.py`, `data_bridge.py` — ネットワーク生成 / データ接続

### pretest（プレテスト層）
- プロモーション施策の事前評価（ポテンシャルモデル）

### ui（UI 層）
- `streamlit_app.py` — Streamlit Web UI

### api（API 層）
- FastAPI エンドポイント（開発中）

## 技術スタック

| カテゴリ | 技術 |
|---|---|
| LLM | Anthropic Claude API |
| データモデル | Pydantic v2 |
| データ処理 | Polars / Pandas / NumPy / SciPy |
| API | FastAPI + Uvicorn |
| UI | Streamlit |
| ベクトルDB | ChromaDB / Qdrant |
| 埋め込み | sentence-transformers |
| ABM | Mesa 3.x |
| 設定管理 | OmegaConf + python-dotenv |
| ロギング | structlog |
| テスト | pytest + hypothesis |
| コード品質 | ruff / mypy |

## 開発共通

- パッケージ管理: `uv venv`, `uv sync`, `uv add <package>`
- テスト: `uv run pytest`
- コード品質: `uv run ruff check .`

## 2階層 RAG の考え方

生活者ペルソナのプロンプトは **セグメントプロファイル（層①）** と
**ベクトルDB 検索結果（層②）** の2段構えで文脈を注入する。

- **層①**: 年代 × 性別 × ライフステージ等で集計された定量的プロファイル
  （k-匿名性を担保した粒度）
- **層②**: 個別の自由回答・定性インサイトをベクトルDBから検索し、
  確信度ラベル付きで提示

この構造により、LLM は「データに根拠のある発言」と「推論による発言」を明確に区別して
振る舞うことができる。
