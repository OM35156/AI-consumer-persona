# AI-Consumer-Persona Claude Code 指示

開発ルールの詳細は [CONTRIBUTING.md](CONTRIBUTING.md) を参照すること。
プロジェクトの構成・規約・用語は [ai_docs/](ai_docs/) を参照すること。

---

## 作業開始前に必ずやること

1. 作業に対応する Issue が存在するか確認する
2. なければ `gh issue create` で Issue を立ててから着手する
3. main を最新にしてからブランチを切る

```bash
git checkout main && git pull origin main
git checkout -b feature/<Issue番号>-<内容>
```

4. `ai_docs/architecture.md` と `ai_docs/coding_standards.md` を読む

---

## ブランチ・コミット

- ブランチ名: `feature/<Issue番号>-<内容>` / `fix/<Issue番号>-<内容>` / `chore/<Issue番号>-<内容>`
- コミットメッセージ: Conventional Commits 形式 + 日本語説明
  - 例: `feat: ペルソナビルダーに属性フィルタリング機能を追加`
- main への直接 push は禁止。必ず PR を通す

---

## PR のルール

- **PR を作成する前に、必ずユーザーに確認を取ること**
- `gh pr create` で PR を作成する（Draft PR: `--draft` フラグ）
- マージ方式は **Squash and merge**
- 本文に `Closes #<Issue番号>` を必ず記載する
- Reviewers に相手を必ず指定する
- 自分の PR は自分でマージしない（`chore/` 系の軽微な変更のみセルフマージ可）

---

## マージ後にやること

```bash
git checkout main && git pull origin main
```

---

## 安全運用の 3 原則

全ての Issue 対応で以下を守ること。

### 1. 出力契約
- すべて Markdown で出力
- 各ステップ終了時に「作業ログ」をイシューにコメント
- エラー/不明点は「質問」節で列挙し停止（自己判断で進めない）

### 2. スコープ境界
- Issue に記載された **許可パス** 以外は変更しない
- 変更が必要な場合は必ずイシューで承認を得てから実施

### 3. 安全弁
- 必ず **Draft PR** で作成する
- 10 ファイル / 500 行を超える変更は分割コミット（理由をログに記載）

---

## Claude Code 固有の注意点

- 1 Issue = 1 PR = 1 機能を守り、スコープを広げない
- `.env` ファイルの内容を読み取ったり表示したりしない
- 調査結果・提案・バグ修正の記録は `ai_docs/` に残す

---

## ai_docs の使い方

| ファイル | 参照タイミング |
|---|---|
| [architecture.md](ai_docs/architecture.md) | 全タスク共通。変更対象のファイルを特定するために |
| [coding_standards.md](ai_docs/coding_standards.md) | コード生成・レビュー前に必ず確認 |
| [glossary.md](ai_docs/glossary.md) | 業務用語・設問タイプ等が出てきたときに |
| `ai_docs/analysis/` | 過去の調査レポートを参照・新規作成 |
| `ai_docs/suggestions/` | 技術提案を記録 |
| `ai_docs/fixes/` | バグ修正の詳細を記録 |
