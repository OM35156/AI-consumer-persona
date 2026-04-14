# ai_docs

Claude Code がタスクを実行する際に参照するドキュメントを格納するディレクトリ。
**Issue を渡す前に必ずこのディレクトリを参照すること。**

## ディレクトリ構成

```
ai_docs/
├── README.md            ← このファイル（使い方）
├── architecture.md      ← システムアーキテクチャ概要
├── coding_standards.md  ← コーディング規約
├── glossary.md          ← 用語集・略語集
├── analysis/            ← 調査レポート（Investigation / RFC タスクの成果物）
│   └── <Issue番号>-*.md
├── suggestions/         ← Claude からの技術的提案
│   └── <Issue番号>-*.md
└── fixes/               ← バグ修正の詳細記録
    └── <Issue番号>-*.md
```

## 各ドキュメントの役割

| ファイル | 読むべきタイミング |
|---|---|
| `architecture.md` | 全タスク共通。どのファイルを変更すべきか判断するために |
| `coding_standards.md` | コード生成・レビュー前に必ず確認 |
| `glossary.md` | 業務用語・ドメイン用語が出てきたときに確認 |
| `analysis/` | 同領域の調査結果が過去にあれば参照 |
| `suggestions/` | 技術的提案の蓄積。重複提案を避けるために確認 |
| `fixes/` | 類似バグの修正履歴を確認するために |

## 更新ルール

- 新しい知見・設計決定があれば積極的にドキュメント化する
- ファイル名は `<Issue番号>-<内容の短い説明>.md` 形式（例: `008-survey-type-analysis.md`）
- 古くなった情報は更新・削除する（放置しない）
- 機密情報（APIキー、個人情報等）は絶対に書かない
