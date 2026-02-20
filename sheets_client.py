"""
GoogleスプレッドシートをTodoの永続化先として利用するクライアントモジュール。
責務: Sheets APIとの通信、CRUD操作のみ。
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
import gspread
import google.auth
from google.oauth2.service_account import Credentials


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _get_google_credentials():
    """
    Google 認証情報を取得して返す。

    優先順位:
    1) GOOGLE_SERVICE_ACCOUNT_JSON_PATH（ローカル向け）
    2) GOOGLE_SERVICE_ACCOUNT_JSON（Render 等: 1行JSON）
    3) Application Default Credentials（Cloud Run / gcloud ADC 等: JSONキー不要）
    """
    import json

    path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON_PATH")
    if path:
        path = os.path.expanduser(path)
        if not os.path.isfile(path):
            raise RuntimeError(f"認証ファイルが見つかりません: {path}")
        with open(path, "r", encoding="utf-8") as f:
            info = json.load(f)
        return Credentials.from_service_account_info(info, scopes=SCOPES)

    json_str = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if json_str:
        json_str = json_str.strip()
        if not json_str:
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON が空です。正しいJSON文字列を設定してください。")
        try:
            info = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"GOOGLE_SERVICE_ACCOUNT_JSON のJSON解析に失敗しました: {e}. "
                "JSONは1行（minify）で貼り付けてください。"
            )
        return Credentials.from_service_account_info(info, scopes=SCOPES)

    # Cloud Run 等: サービスに割り当てたサービスアカウントでADCを利用（JSONキー不要）
    try:
        creds, _project_id = google.auth.default(scopes=SCOPES)
    except Exception as e:
        raise RuntimeError(
            "Google 認証情報を取得できませんでした。"
            "Cloud Run を使う場合は、Cloud Run サービスにサービスアカウントを割り当ててください。"
            "または GOOGLE_SERVICE_ACCOUNT_JSON(_PATH) を設定してください。"
            f"（詳細: {e}）"
        )

    # 一部の認証情報は明示的にスコープ付与が必要
    if getattr(creds, "requires_scopes", False) and hasattr(creds, "with_scopes"):
        creds = creds.with_scopes(SCOPES)
    return creds


def _get_client():
    """gspreadクライアントを取得。環境変数から認証情報を読む。"""
    spreadsheet_id = os.environ.get("SPREADSHEET_ID", "").strip()
    if not spreadsheet_id:
        raise RuntimeError(
            "SPREADSHEET_ID が設定されていません。"
            "スプレッドシートURLの /d/ と /edit の間の文字列を設定してください。"
        )

    creds = _get_google_credentials()
    client = gspread.authorize(creds)
    return client.open_by_key(spreadsheet_id)


def _get_sheet():
    """対象シートを取得。"""
    spreadsheet = _get_client()
    sheet_name = os.environ.get("SHEET_NAME", "todos").strip() or "todos"
    return spreadsheet.worksheet(sheet_name)


def _ensure_headers(worksheet):
    """ヘッダ行が存在することを確認。なければ作成。"""
    try:
        first_row = worksheet.row_values(1)
    except Exception:
        first_row = []
    headers = ["id", "title", "body", "due_date", "created_at", "updated_at"]
    if not first_row or (len(first_row) > 0 and first_row[0] != "id"):
        worksheet.update("A1:F1", [headers], value_input_option="USER_ENTERED")


def _row_to_dict(row: list, headers: list) -> dict:
    """行データをdictに変換。"""
    d = {}
    for i, h in enumerate(headers):
        d[h] = row[i] if i < len(row) else ""
    return d


def _dict_to_row(d: dict, headers: list) -> list:
    """dictを行データに変換。"""
    return [str(d.get(h, "")) for h in headers]


def fetch_all_todos() -> list[dict]:
    """
    全Todoを取得してリストで返す。
    接続失敗時は例外を投げる（呼び出し側でキャッチ）。
    """
    sheet = _get_sheet()
    _ensure_headers(sheet)
    records = sheet.get_all_records()
    # get_all_recordsは1行目をヘッダとして扱う
    return [dict(r) for r in records if r.get("id")]


def fetch_todo_by_id(todo_id):
    """指定IDのTodoを1件取得。見つからなければ None。"""
    sheet = _get_sheet()
    _ensure_headers(sheet)
    headers = ["id", "title", "body", "due_date", "created_at", "updated_at"]
    rows = sheet.get_all_values()
    if len(rows) < 2:
        return None
    # 1行目はヘッダ
    for i, row in enumerate(rows[1:], start=2):
        if len(row) > 0 and row[0] == todo_id:
            return _row_to_dict(row, headers)
    return None


def create_todo(title: str, body: str, due_date: str) -> None:
    """新規Todoを1件登録。"""
    sheet = _get_sheet()
    _ensure_headers(sheet)
    now = datetime.now(timezone.utc).isoformat()
    row = [str(uuid.uuid4()), title, body, due_date, now, now]
    sheet.append_row(row, value_input_option="USER_ENTERED")


def update_todo(todo_id: str, title: str, body: str, due_date: str) -> None:
    """指定IDのTodoを更新。存在しない場合は何もしない。"""
    sheet = _get_sheet()
    _ensure_headers(sheet)
    rows = sheet.get_all_values()
    if len(rows) < 2:
        return
    headers = ["id", "title", "body", "due_date", "created_at", "updated_at"]
    for i, row in enumerate(rows[1:], start=2):
        if len(row) > 0 and row[0] == todo_id:
            created_at = row[4] if len(row) > 4 else ""
            now = datetime.now(timezone.utc).isoformat()
            new_row = [todo_id, title, body, due_date, created_at, now]
            sheet.update(f"A{i}:F{i}", [new_row], value_input_option="USER_ENTERED")
            return
