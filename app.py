"""
TodoリストWebアプリ - Flaskメインアプリケーション。
ルーティング・バリデーション・テンプレート描画に専念。
Sheets操作は sheets_client に委譲。
"""
import os

from dotenv import load_dotenv

load_dotenv()

from flask import Flask, flash, redirect, render_template, request, url_for

import sheets_client

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")


def _validate_form(title, due_date):
    """フォームバリデーション。エラーメッセージのリストを返す。"""
    errors = []
    if not title or not title.strip():
        errors.append("タイトルは必須です。")
    if not due_date or not due_date.strip():
        errors.append("期日は必須です。")
    return errors


@app.route("/")
def index():
    """Todo一覧ページ。"""
    try:
        todos = sheets_client.fetch_all_todos()
    except Exception as e:
        flash(f"データの取得に失敗しました: {e}", "error")
        todos = []
    return render_template("index.html", todos=todos)


@app.route("/new", methods=["GET"])
def new_get():
    """新規作成フォームを表示。"""
    return render_template("new.html")


@app.route("/new", methods=["POST"])
def new_post():
    """新規作成処理。"""
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    due_date = request.form.get("due_date", "").strip()

    errors = _validate_form(title, due_date)
    if errors:
        for msg in errors:
            flash(msg, "error")
        return render_template("new.html", title=title, body=body, due_date=due_date), 400

    try:
        sheets_client.create_todo(title, body, due_date)
        flash("Todoを登録しました。", "success")
        return redirect(url_for("index"))
    except Exception as e:
        flash(f"登録に失敗しました: {e}", "error")
        return render_template("new.html", title=title, body=body, due_date=due_date), 500


@app.route("/edit/<id>", methods=["GET"])
def edit_get(id: str):
    """編集フォームを表示。"""
    todo = sheets_client.fetch_todo_by_id(id)
    if todo is None:
        flash("指定されたTodoが見つかりません。", "error")
        return redirect(url_for("index"))
    return render_template("edit.html", todo=todo)


@app.route("/edit/<id>", methods=["POST"])
def edit_post(id: str):
    """更新処理。"""
    todo = sheets_client.fetch_todo_by_id(id)
    if todo is None:
        flash("指定されたTodoが見つかりません。", "error")
        return redirect(url_for("index"))

    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    due_date = request.form.get("due_date", "").strip()

    errors = _validate_form(title, due_date)
    if errors:
        for msg in errors:
            flash(msg, "error")
        return render_template("edit.html", todo={**todo, "title": title, "body": body, "due_date": due_date}), 400

    try:
        sheets_client.update_todo(id, title, body, due_date)
        flash("Todoを更新しました。", "success")
        return redirect(url_for("index"))
    except Exception as e:
        flash(f"更新に失敗しました: {e}", "error")
        return render_template("edit.html", todo={**todo, "title": title, "body": body, "due_date": due_date}), 500


@app.errorhandler(500)
def internal_error(e):
    """500エラー時も画面を表示（Sheets接続失敗等）。"""
    return render_template("error.html", message=str(e)), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))  # 5000はmacOSのAirPlayと競合しやすいため5001を使用
    app.run(debug=True, host="0.0.0.0", port=port)
