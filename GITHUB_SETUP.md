# GitHub プッシュ手順

このドキュメントは、python-web-todo-app を GitHub に正しくプッシュするための手順です。

---

## 1. .gitignore の内容

プロジェクトルートに `.gitignore` を配置し、以下の内容を設定してください。

```
# ===== 秘密情報（絶対にGitに含めない） =====
.env
credentials.json
service-account*.json
*-credentials.json
line-calendar-bot-*.json
*.pem

# ===== Python =====
__pycache__/
*.py[cod]
*$py.class
.Python
venv/
.venv/
env/
*.egg-info/
.eggs/
dist/
build/

# ===== IDE =====
.idea/
.vscode/
*.swp
*.swo

# ===== OS =====
.DS_Store
Thumbs.db
*.log
```

---

## 2. 初回コミット手順

### ステップ 2-1: Git リポジトリを初期化

```bash
cd /Applications/cursorフォルダ/python-web-todo-app
git init
```

### ステップ 2-2: 除外されるファイルを確認（重要）

以下を実行し、`.env` やサービスアカウント JSON が **表示されない** ことを確認する。

```bash
git status
```

期待する結果: `.env`、`line-calendar-bot-*.json` が Untracked に **含まれていない** こと。

### ステップ 2-3: ファイルをステージング

```bash
git add .
```

### ステップ 2-4: ステージング内容を再確認

```bash
git status
```

確認ポイント:
- `app.py`、`sheets_client.py`、`templates/`、`static/`、`requirements.txt` 等が含まれている
- `.env` や `*.json`（サービスアカウント）が **含まれていない**

### ステップ 2-5: 初回コミット

```bash
git commit -m "Initial commit: Flask Todo app with Google Sheets"
```

---

## 3. GitHub 新規リポジトリ作成後の接続手順

### ステップ 3-1: GitHub でリポジトリを作成

1. [GitHub](https://github.com) にログイン
2. 右上の「+」→「New repository」
3. 以下を設定:
   - **Repository name:** `python-web-todo-app`
   - **Description:** （任意）Flask Todo app with Google Sheets
   - **Public** を選択
   - **Add a README file** はチェック **しない**（既存の README を使うため）
4. 「Create repository」をクリック

### ステップ 3-2: リモートを追加

GitHub 作成後、表示される URL を使う。**自分のユーザー名に置き換えること。**

```bash
git remote add origin https://github.com/YOUR_USERNAME/python-web-todo-app.git
```

例: ユーザー名が `tanaka` の場合
```bash
git remote add origin https://github.com/tanaka/python-web-todo-app.git
```

### ステップ 3-3: リモート設定の確認

```bash
git remote -v
```

---

## 4. Push 完了までのコマンド（順番通り）

### 4-1. ブランチ名を確認

```bash
git branch
```

表示が `* main` または `* master` であることを確認。

### 4-2. ブランチを main に統一（必要な場合）

古い Git では `master` になっていることがある。

```bash
git branch -M main
```

### 4-3. 初回プッシュ

```bash
git push -u origin main
```

GitHub の認証（ユーザー名・パスワードまたはトークン）を求められたら入力する。

### 4-4. プッシュ結果の確認

GitHub のリポジトリページを開き、ファイルがアップロードされていることを確認する。

**確認ポイント:**
- `.env` が **含まれていない**
- `line-calendar-bot-*.json` が **含まれていない**
- `app.py`、`sheets_client.py`、`templates/`、`static/` 等が含まれている

---

## 5. デプロイを想定した requirements.txt

Render 等の PaaS で使用する `requirements.txt` の例です。バージョンを固定すると再現性が高まります。

```
# Web フレームワーク
Flask>=3.0.0,<4.0.0

# 環境変数読み込み
python-dotenv>=1.0.0

# Google Sheets API
gspread>=6.0.0
google-auth>=2.0.0

# 本番用 WSGI サーバー
gunicorn>=21.0.0
```

---

## トラブルシューティング

### Q: `git push` で認証エラーになる

**A:** GitHub はパスワードではなく **Personal Access Token (PAT)** を使います。

1. GitHub → Settings → Developer settings → Personal access tokens
2. 「Generate new token」でトークン作成
3. パスワードの代わりにそのトークンを入力

### Q: `.env` が誤ってコミットされそうになった

**A:** 以下でステージングから外し、再度コミットする。

```bash
git reset HEAD .env
```

その後、`.gitignore` に `.env` が含まれているか確認する。

### Q: すでに `.env` をコミットしてしまった

**A:** 履歴から削除する必要がある。以下のコマンドは慎重に実行する。

```bash
git rm --cached .env
git commit -m "Remove .env from tracking"
git push
```

**注意:** 既にプッシュ済みの場合、`.env` の内容は履歴に残る。トークン等は必ず再発行する。
