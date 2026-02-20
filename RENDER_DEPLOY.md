# Render デプロイ完全ガイド

Flask Todo アプリ（Google Sheets 連携）を Render で公開する手順とトラブルシューティング。

---

## 1. 最短手順（チェックリスト）

### 事前準備

- [ ] GitHub に Push 済み（kuroroyumi-wq/python-web-todo-app）
- [ ] Render にログインし、GitHub 連携済み
- [ ] スプレッドシートをサービスアカウントと共有済み（下記「共有設定」参照）

### Render Configure 画面での設定

- [ ] **Build Command:** `pip install -r requirements.txt`
- [ ] **Start Command:** `gunicorn app:app` または Procfile を利用

### Environment Variables（必須4つ）

| Key | Value の取得方法 |
|-----|------------------|
| `SPREADSHEET_ID` | スプレッドシートURLの `/d/` と `/edit` の間の文字列 |
| `SHEET_NAME` | シートタブ名（例: `シート1` または `todos`） |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | 下記「JSON貼り付け方法」参照 |
| `SECRET_KEY` | `python3 -c "import secrets; print(secrets.token_hex(32))"` で生成 |

### デプロイ実行

- [ ] **Create Web Service** をクリック
- [ ] Build が成功するまで待つ
- [ ] 発行URLにアクセスして動作確認

---

## 2. Environment Variables 詳細

### SPREADSHEET_ID

**URL例:** `https://docs.google.com/spreadsheets/d/1_lx5KVD_3er8tSmiePlYW9cB-RR_4eIb2O0GjsF5ZoU/edit`

**抜き出す部分:** `/d/` の直後から `/edit` の直前まで

```
1_lx5KVD_3er8tSmiePlYW9cB-RR_4eIb2O0GjsF5ZoU
```

### SHEET_NAME

**重要:** スプレッドシート下部のタブ名と**完全一致**させる。

- 新規作成のデフォルト: `シート1`
- 手動でリネームした場合: `todos` など、その名前

### GOOGLE_SERVICE_ACCOUNT_JSON（貼り付け方法）

**注意点:**
- Render の Environment Variables は**1行**が原則
- 改行を含むと正しく読み込まれない場合がある
- 引用符（`"` `'`）で囲まない。値のみ貼り付ける

**手順:**

1. ターミナルで以下を実行し、1行の JSON を表示する
   ```bash
   cd /Applications/cursorフォルダ/python-web-todo-app
   python3 -c "import json; print(json.dumps(json.load(open('line-calendar-bot-484506-06db6546d685.json'))))"
   ```
2. 表示された文字列を**そのまま**コピー（先頭・末尾の空白に注意）
3. Render の Value 欄に貼り付け

**改行・エスケープ問題の対処:**
- 必ず上記の minify 済み JSON を使用する
- 手動コピーする場合は [codebeautify.org/jsonminifier](https://codebeautify.org/jsonminifier) で1行に変換
- Value 欄では `"` や `'` で囲まない（Render が自動処理する）

### SECRET_KEY（本番必須）

Flask のセッション署名用。未設定だとセッションが不安定になる。

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

生成された64文字の hex をそのまま `SECRET_KEY` に設定する。

---

## 3. スプレッドシート共有設定（チェックリスト）

サービスアカウントがスプレッドシートにアクセスするために必須。

- [ ] スプレッドシートを開く
- [ ] 右上の「**共有**」をクリック
- [ ] JSON 内の `client_email` を追加
  - 例: `todo-app-sheets@line-calendar-bot-484506.iam.gserviceaccount.com`
- [ ] 権限を「**編集者**」に設定
- [ ] 「送信」または「共有」をクリック

**client_email の確認方法:**
```bash
python3 -c "import json; d=json.load(open('line-calendar-bot-484506-06db6546d685.json')); print(d['client_email'])"
```

---

## 4. デプロイ後エラー対処表

| 症状 | 原因 | 確認方法 | 修正方法 |
|------|------|----------|----------|
| **ModuleNotFoundError: No module named 'xxx'** | requirements.txt にパッケージが含まれていない | Build Log を確認 | requirements.txt に該当パッケージを追加し、再デプロイ |
| **gunicorn: error: ... No module named 'app'** | app:app の参照ミス、または app.py がルートにない | リポジトリ構成を確認 | Start Command を `gunicorn app:app` に統一。ルート直下に app.py があることを確認 |
| **500 Internal Server Error**（起動直後） | 環境変数未設定、JSON パース失敗、Sheets 権限不足 | Logs タブで traceback を確認 | SPREADSHEET_ID, GOOGLE_SERVICE_ACCOUNT_JSON, SHEET_NAME を確認。JSON を1行で再貼り付け |
| **RuntimeError: GOOGLE_SERVICE_ACCOUNT_JSON のJSON解析に失敗** | JSON に改行・不正文字が含まれている | 環境変数の Value を再確認 | minify 済み JSON で再設定 |
| **RuntimeError: SPREADSHEET_ID が設定されていません** | 環境変数が未設定 | Environment Variables 一覧を確認 | SPREADSHEET_ID を追加 |
| **gspread.exceptions.APIError: 403 / permission denied** | スプレッドシートがサービスアカウントと共有されていない | 共有設定を確認 | 上記「共有設定」を実施 |
| **gspread.exceptions.SpreadsheetNotFound** | SPREADSHEET_ID が間違っている、または共有されていない | ID を URL と照合 | 正しい ID を設定し、共有を確認 |
| **WorksheetNotFound: シート名** | SHEET_NAME が実際のシート名と一致していない | スプレッドシートのタブ名を確認 | SHEET_NAME をタブ名と完全一致させる |

---

## 5. Render 操作手順（クリック順）

1. **Dashboard** → **New +** → **Web Service**
2. リポジトリ一覧から **kuroroyumi-wq/python-web-todo-app** を選択 → **Connect**
3. **Name:** `python-web-todo-app`（任意）
4. **Build Command:** `pip install -r requirements.txt`
5. **Start Command:** `gunicorn app:app`（Procfile があれば自動検出される場合あり）
6. **Environment** セクション → **Add Environment Variable**
   - `SPREADSHEET_ID` → 値
   - `SHEET_NAME` → 値
   - `GOOGLE_SERVICE_ACCOUNT_JSON` → 1行の JSON
   - `SECRET_KEY` → 生成したトークン
7. **Create Web Service** をクリック
8. Build 完了を待つ（Logs で進捗確認）
9. 発行された URL（例: `https://python-web-todo-app-xxx.onrender.com`）にアクセス
10. Todo 一覧が表示されれば成功

---

## 6. コード堅牢化（適用済み）

以下の対応をコードに反映済みです。

- `sheets_client.py`: GOOGLE_SERVICE_ACCOUNT_JSON の前後空白・改行を除去してから `json.loads`
- `sheets_client.py`: 環境変数未設定時のエラーメッセージを明確化
- `Procfile`: `--bind 0.0.0.0:${PORT:-5000}` で PORT 対応（Render は PORT を自動設定）
- `app.py`: `SECRET_KEY` を環境変数から取得（本番では必ず設定すること）
