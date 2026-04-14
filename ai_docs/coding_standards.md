# コーディング規約

詳細は `CLAUDE.md` および `CONTRIBUTING.md` も参照すること。

---

## 言語・応答

- コード内のコメント・docstring は **日本語** で記述する
- 変数名・関数名・クラス名は **英語**（Python の慣習に従う）

## Python スタイル

### 基本
- PEP 8 準拠
- 最大行長: **120 文字**
- Python **3.11 以上** を前提とする

### 型ヒント
```python
# ✅ 良い例：引数・戻り値に必ず型ヒントを付ける
def get_physician(physician_id: int) -> Physician | None:
    ...

# ❌ 悪い例：型ヒントなし
def get_physician(physician_id):
    ...
```

### 命名規則

| 対象 | 規則 | 例 |
|---|---|---|
| 変数・関数 | `snake_case` | `physician_id`, `get_persona()` |
| クラス | `PascalCase` | `PersonaBuilder`, `PhysicianProfile` |
| 定数 | `UPPER_SNAKE_CASE` | `API_BASE_URL`, `MAX_RETRIES` |
| プライベート | `_先頭アンダースコア` | `_internal_cache` |

### インポート順序
```python
# 1. 標準ライブラリ
import json
from pathlib import Path

# 2. サードパーティ（空行で区切る）
import anthropic
from pydantic import BaseModel

# 3. ローカル（空行で区切る）
from .profile import PhysicianProfile
```

### 文字列フォーマット
```python
# ✅ f-string を優先
message = f"Physician {physician_id} not found"

# ❌ .format() や % は使わない
message = "Physician {} not found".format(physician_id)
```

### パス操作
```python
# ✅ pathlib を使う
from pathlib import Path
output_dir = Path("output") / "results"

# ❌ os.path は使わない
import os
output_dir = os.path.join("output", "results")
```

---

## データ処理

```python
# ✅ データフレーム操作は polars を優先
import polars as pl

# ❌ pandas は第二選択
import pandas as pd
```

---

## エラーハンドリング

```python
# ✅ 具体的な例外クラスを指定する
try:
    response = client.messages.create(...)
except anthropic.APIError as e:
    logger.error(f"Claude API エラー: {e}")
    raise

# ❌ 裸の except は禁止
try:
    ...
except:  # noqa
    pass
```

---

## セキュリティ

- APIキー・パスワード・トークンをコードに **ハードコードしない**
- 機密情報は `.env` ファイルで管理（`.gitignore` に含める）
- SQL クエリは **パラメータ化クエリ** を使用（文字列結合禁止）
- ユーザー入力は必ずバリデーションする
- ログに機密情報を出力しない

---

## ファイル操作

```python
# ✅ encoding を明示する
with open(file_path, encoding="utf-8") as f:
    content = f.read()
```

---

## やってはいけないこと

- ❌ `print()` をデバッグ目的でコミットする（`logger` を使う）
- ❌ `.env` ファイルをコミットする
- ❌ `except:` や `except Exception:` を何もせず握りつぶす
- ❌ グローバル変数の使用
