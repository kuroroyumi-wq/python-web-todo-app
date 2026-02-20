"""
TodoリストWebアプリ - Flaskメインアプリケーション。
ルーティング・バリデーション・テンプレート描画に専念。
Sheets操作は sheets_client に委譲。
"""
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

from flask import Flask, flash, redirect, render_template, request, url_for

import sheets_client

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

logger = logging.getLogger(__name__)

PRIORITY_RANK = {"High": 0, "Medium": 1, "Low": 2}
_PRIORITY_JA = {"High": "高", "Medium": "中", "Low": "低"}
_STATUS_JA = {"open": "未完了", "done": "完了"}


# ── Timezone helper ──────────────────────────────────────────────────

def _get_tz() -> ZoneInfo:
    name = os.environ.get("APP_TIMEZONE", "Asia/Tokyo").strip()
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("Asia/Tokyo")


# ── Template filters ─────────────────────────────────────────────────

@app.template_filter("priority_ja")
def priority_ja_filter(value):
    """High→高 / Medium→中 / Low→低"""
    return _PRIORITY_JA.get(value, value or "中")


@app.template_filter("status_ja")
def status_ja_filter(value):
    """open→未完了 / done→完了"""
    return _STATUS_JA.get(value, value or "未完了")


@app.template_filter("iso_to_date")
def iso_to_date_filter(value):
    """ISO8601 → YYYY-MM-DD（date input 用）。"""
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return str(value)[:10] if len(str(value)) >= 10 else str(value)


@app.template_filter("format_date")
def format_date_filter(value):
    """ISO8601 → 表示用日付。"""
    if not value:
        return "-"
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return str(value)


@app.template_filter("format_datetime")
def format_datetime_filter(value):
    """ISO8601 → 表示用日時。"""
    if not value:
        return "-"
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return str(value)


# ── Helpers ──────────────────────────────────────────────────────────

def _date_to_iso(date_str: str) -> str:
    """HTML date input (YYYY-MM-DD) → ISO8601 TZ 付き (23:59)。空なら空。"""
    if not date_str or not date_str.strip():
        return ""
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        dt = dt.replace(hour=23, minute=59, second=0, tzinfo=_get_tz())
        return dt.isoformat()
    except ValueError:
        return date_str.strip()


def _validate_form(title: str) -> list[str]:
    errors = []
    if not title or not title.strip():
        errors.append("タイトルは必須です。")
    return errors


def _sort_todos(todos: list[dict], sort_key: str) -> list[dict]:
    if sort_key == "priority":
        return sorted(
            todos,
            key=lambda t: PRIORITY_RANK.get(t.get("priority", "Medium"), 1),
        )
    if sort_key == "due":
        return sorted(
            todos,
            key=lambda t: t.get("due_at") or "\uffff",
        )
    if sort_key == "updated":
        return sorted(
            todos,
            key=lambda t: t.get("updated_at") or "",
            reverse=True,
        )
    return todos


# ── Routes ───────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Todo一覧。sort / status クエリでソート・フィルタ。"""
    sort = request.args.get("sort", "")
    status_filter = request.args.get("status", "all")

    try:
        todos = sheets_client.fetch_all_todos()
    except Exception as e:
        flash(f"データの取得に失敗しました: {e}", "error")
        todos = []

    if status_filter == "open":
        todos = [t for t in todos if t.get("status") != "done"]

    todos = _sort_todos(todos, sort)

    return render_template(
        "index.html", todos=todos, sort=sort, status=status_filter,
    )


@app.route("/new", methods=["GET"])
def new_get():
    """新規作成フォームを表示。"""
    return render_template("new.html")


@app.route("/new", methods=["POST"])
def new_post():
    """新規作成処理。"""
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    due_date = request.form.get("due_date", "").strip()
    priority = request.form.get("priority", "Medium").strip()

    errors = _validate_form(title)
    if errors:
        for msg in errors:
            flash(msg, "error")
        return render_template(
            "new.html",
            title=title, description=description,
            due_date=due_date, priority=priority,
        ), 400

    try:
        sheets_client.create_todo(
            title=title,
            description=description,
            priority=priority,
            due_at=_date_to_iso(due_date),
        )
        flash("Todoを登録しました。", "success")
        return redirect(url_for("index"))
    except Exception as e:
        flash(f"登録に失敗しました: {e}", "error")
        return render_template(
            "new.html",
            title=title, description=description,
            due_date=due_date, priority=priority,
        ), 500


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
    description = request.form.get("description", "").strip()
    due_date = request.form.get("due_date", "").strip()
    priority = request.form.get("priority", "Medium").strip()

    errors = _validate_form(title)
    if errors:
        for msg in errors:
            flash(msg, "error")
        merged = {
            **todo,
            "title": title,
            "description": description,
            "priority": priority,
            "due_at": _date_to_iso(due_date) if due_date else todo.get("due_at", ""),
        }
        return render_template("edit.html", todo=merged), 400

    try:
        sheets_client.update_todo(
            todo_id=id,
            title=title,
            description=description,
            priority=priority,
            due_at=_date_to_iso(due_date),
        )
        flash("Todoを更新しました。", "success")
        return redirect(url_for("index"))
    except Exception as e:
        flash(f"更新に失敗しました: {e}", "error")
        merged = {
            **todo,
            "title": title,
            "description": description,
            "priority": priority,
        }
        return render_template("edit.html", todo=merged), 500


@app.route("/todos/<id>/toggle", methods=["POST"])
def toggle_todo(id: str):
    """open↔done をワンクリック切り替え。"""
    new_status = sheets_client.toggle_status(id)
    if new_status is None:
        flash("指定されたTodoが見つかりません。", "error")
    else:
        label = "完了" if new_status == "done" else "未完了"
        flash(f"Todoを{label}にしました。", "success")
    return redirect(request.referrer or url_for("index"))


@app.route("/cron/remind", methods=["POST"])
def cron_remind():
    """Cloud Scheduler から呼ばれるリマインド通知。X-CRON-TOKEN で認証。"""
    expected = os.environ.get("CRON_AUTH_TOKEN", "").strip()
    provided = request.headers.get("X-CRON-TOKEN", "").strip()

    if not expected or provided != expected:
        return {"error": "forbidden"}, 403

    hours = int(os.environ.get("REMIND_WINDOW_HOURS", "24"))

    try:
        due_todos = sheets_client.find_due_within(hours=hours)
    except Exception as e:
        logger.exception("リマインド対象の取得に失敗")
        return {"error": str(e)}, 500

    if not due_todos:
        return {"message": "対象Todoなし", "count": 0}, 200

    lines = [f"⏰ {len(due_todos)}件のTodoが期限間近です:"]
    for t in due_todos:
        due_disp = t.get("due_at", "")[:16] if t.get("due_at") else "期日なし"
        lines.append(f"・{t['title']}（期限: {due_disp}）")

    import line_client
    if line_client.send_push_message("\n".join(lines)):
        sheets_client.mark_reminded([t["id"] for t in due_todos])
        return {"message": "通知完了", "count": len(due_todos)}, 200

    return {"error": "LINE送信失敗"}, 502


@app.errorhandler(500)
def internal_error(e):
    return render_template("error.html", message=str(e)), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=True, host="0.0.0.0", port=port)
