# システムアーキテクチャ

## プロジェクト概要

AI-persona（Digital Twin）は、LLM を活用して医師の AI ペルソナを構築し、
プロモーション反応や処方意向をシミュレーションするシステムである。

## ディレクトリ構成

```
AI-persona/
├── src/digital_twin/        ← メインソースコード
│   ├── api/                 ← API エンドポイント（FastAPI）
│   ├── data/                ← データ読込・スキーマ・匿名化
│   ├── engine/              ← シミュレーションエンジン（プロンプト・実行）
│   ├── evaluation/          ← 評価（メトリクス・バリデーション・可視化）
│   ├── persona/             ← ペルソナ構築・プロファイル管理
│   ├── ui/                  ← Streamlit UI
│   └── utils/               ← 設定読込・コスト計算
├── configs/                 ← 設定ファイル（base.yaml, poc.yaml）
├── data/                    ← データ格納（dummy/raw/processed）
├── scripts/                 ← 実行スクリプト
├── templates/               ← プロンプトテンプレート
├── tests/                   ← テスト（unit/integration/fixtures）
└── ai_docs/                 ← AI 向けドキュメント
```

## 主要モジュール

### data（データ層）
- `loader.py` — データ読込
- `schema.py` — データスキーマ定義（Pydantic）
- `anonymizer.py` — 匿名化処理

### persona（ペルソナ層）
- `builder.py` — ペルソナ構築ロジック
- `profile.py` — 医師プロファイル定義

### engine（シミュレーション層）
- `prompt.py` — LLM プロンプト生成
- `simulator.py` — シミュレーション実行

### evaluation（評価層）
- `metrics.py` — 評価メトリクス計算
- `validator.py` — 結果バリデーション
- `visualization.py` — 結果可視化

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
| ベクトルDB | ChromaDB |
| 設定管理 | OmegaConf + python-dotenv |
| ロギング | structlog |
| テスト | pytest |
| コード品質 | ruff / mypy |

## 開発共通

- パッケージ管理: `uv venv`, `uv sync`, `uv add <package>`
- テスト: `uv run pytest`
- コード品質: `uv run ruff check .`
