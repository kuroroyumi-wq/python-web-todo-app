# Cloud Run デプロイ直前チェックリスト（1分版）

## GCP 側

- [ ] 請求先アカウントが有効
- [ ] Sheets API / Drive API が有効
- [ ] Cloud Run 専用SA作成済み（`cloudrun-todo-sheets`）
- [ ] スプレッドシートにSAを**編集者**で共有済み

## GitHub 側

- [ ] 最新コードが `main` に push 済み
- [ ] `.env` / JSONキーが含まれて**いない**こと

## Cloud Run 設定値

| 項目 | 値 |
|------|------|
| ソース | GitHub: `kuroroyumi-wq/python-web-todo-app` |
| ブランチ | `main` |
| リージョン | `asia-northeast1`（東京）推奨 |
| 認証 | 「未認証の呼び出しを許可」（公開する場合） |
| 実行SA | `cloudrun-todo-sheets@line-calendar-bot-484506.iam.gserviceaccount.com` |

## 環境変数（3つ）

| Key | Value |
|-----|-------|
| `SPREADSHEET_ID` | `1_lx5KVD_3er8tSmiePlYW9cB-RR_4eIb2O0GjsF5ZoU` |
| `SHEET_NAME` | `シート1` |
| `SECRET_KEY` | `python3 -c "import secrets; print(secrets.token_hex(32))"` で生成した値 |

※ `GOOGLE_SERVICE_ACCOUNT_JSON` は**不要**（ADC方式）

## デプロイ後の確認

- [ ] HTTPS URL にアクセス → Todo一覧が表示される
- [ ] 新規作成 → スプレッドシートに反映
- [ ] 編集 → スプレッドシートに反映
