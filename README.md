# Python Web Todo App

## 概要

Flaskを使用したTodo管理Webアプリ。  
データベースとしてGoogleスプレッドシートを利用し、DBサーバー不要で永続化できる構成。

## 使用技術

- Python
- Flask
- HTML / CSS / JavaScript（必要最小限）
- Jinja2
- Google Sheets API（gspread）
- GCP（サービスアカウント認証）
- Git / GitHub

## 機能

- **Todo登録** … タイトル・内容・期日を入力して登録
- **Todo編集** … 既存のTodoを編集して更新
- **Todo一覧表示** … 登録済みTodoの一覧を表示

## データ構造

| 列名 | 説明 |
|------|------|
| id | 一意の識別子（UUID） |
| title | タイトル |
| body | 内容 |
| due_date | 期日（YYYY-MM-DD） |
| created_at | 作成日時（ISO形式） |
| updated_at | 更新日時（ISO形式） |

## 公開URL

（デプロイ後に記載）

---

## ディレクトリ構成

```
python-web-todo-app/
├── app.py              # Flaskメイン（ルーティング・バリデーション）
├── sheets_client.py     # Google Sheets操作（責務分離）
├── requirements.txt
├── Procfile             # デプロイ用（gunicorn起動）
├── .env                 # 環境変数（Git除外）
├── .env.example         # 環境変数テンプレート
├── .gitignore
├── static/
│   └── style.css
└── templates/
    ├── base.html
    ├── index.html
    ├── new.html
    ├── edit.html
    └── error.html
```

---

## ローカル実行手順

### 1. 依存関係のインストール

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. GCP設定（サービスアカウント）

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクト作成
2. 「APIとサービス」→「ライブラリ」で **Google Sheets API** と **Google Drive API** を有効化
3. 「認証情報」→「サービスアカウントを作成」→ 鍵を JSON でダウンロード
4. スプレッドシートを新規作成し、**サービスアカウントのメール（xxx@xxx.iam.gserviceaccount.com）を編集者として共有**

### 3. 環境変数の設定

`.env` ファイルを作成し、以下を設定する。

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `SPREADSHEET_ID` | ✅ | スプレッドシートID（URLの `/d/` と `/edit` の間） |
| `SHEET_NAME` | - | シート名（デフォルト: `todos`。新規シートは「シート1」） |
| `GOOGLE_SERVICE_ACCOUNT_JSON_PATH` | ✅ | 認証JSONファイルのフルパス（**推奨・minify不要**） |
| `SECRET_KEY` | - | Flaskセッション用（本番では必ず設定） |

**方法A（推奨・ローカル）:** JSONファイルのパスを指定

```
GOOGLE_SERVICE_ACCOUNT_JSON_PATH=/path/to/line-calendar-bot-xxx.json
```

**方法B（デプロイ時）:** JSONを1行にした文字列

```
GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
```

`.env.example` をコピーして `.env` を作成し、値を設定すればよい。

### 4. 起動

```bash
python app.py
```

ブラウザで **http://localhost:5001** にアクセス。  
（5000はmacOSのAirPlayと競合するため、デフォルトは5001）

---

## デプロイ手順（Render / Railway 想定）

### 環境変数一覧

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `SPREADSHEET_ID` | ✅ | スプレッドシートID |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | ✅ | サービスアカウントJSON（1行の文字列） |
| `SHEET_NAME` | - | シート名（デフォルト: `todos`） |
| `SECRET_KEY` | ✅ | Flaskセッション署名用 |
| `PORT` | - | PaaSが自動設定することが多い |

### 起動コマンド

```bash
gunicorn app:app --bind 0.0.0.0:${PORT:-5000}
```

Procfile に上記を記載済み。Render / Railway ではリポジトリ連携後、環境変数を設定すればデプロイ可能。

### 注意

- デプロイ先では `GOOGLE_SERVICE_ACCOUNT_JSON` を使用（ファイルパスは使えない）
- スプレッドシートはサービスアカウントのメールで編集権限を付与すること

---

## 学んだこと

- **外部APIとの連携** … Google Sheets API（gspread）によるデータ永続化
- **サービスアカウント認証** … GCPの鍵管理、スプレッドシート共有
- **環境変数管理** … `.env`、`python-dotenv`、秘密情報の扱い
- **MVC的な責務分離設計** … `app.py`（ルーティング・バリデーション）と `sheets_client.py`（Sheets操作）の分離
- **PaaSデプロイ** … Procfile、gunicorn、環境変数による本番設定
