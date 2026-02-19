"""
GoogleスプレッドシートをTodoの永続化先として利用するクライアントモジュール。
責務: Sheets APIとの通信、CRUD操作のみ。
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
import gspread
from google.oauth2.service_account import Credentials


def _get_credentials_info():
    """
    認証情報のdictを返す。
    GOOGLE_SERVICE_ACCOUNT_JSON_PATH が設定されていればファイルから読み込む（そのまま貼り付け不要）。
    なければ GOOGLE_SERVICE_ACCOUNT_JSON の文字列を使用。
    """
    import json

    path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON_PATH")
    if path:
        # ファイルパス指定 → そのままのJSONファイルを読み込み（minify不要）
        path = os.path.expanduser(path)
        if not os.path.isfile(path):
            raise RuntimeError(f"認証ファイルが見つかりません: {path}")
        with open(path, "r", encoding="utf-8") as f:
            info = json.load(f)
        return info

    json_str = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not json_str:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON または GOOGLE_SERVICE_ACCOUNT_JSON_PATH を設定してください。"
            "JSON_PATH を使うと、JSONを1行にする必要がありません。"
        )
    try:
        info = json.loads(json_str)
    except Exception as e:
        raise RuntimeError(f"GOOGLE_SERVICE_ACCOUNT_JSON のJSON解析に失敗しました: {e}")
    return info


def _get_client():
    """gspreadクライアントを取得。環境変数から認証情報を読む。"""
    info = _get_credentials_info()

    spreadsheet_id = os.environ.get("SPREADSHEET_ID")
    if not spreadsheet_id:
        raise RuntimeError("SPREADSHEET_ID が設定されていません。")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(spreadsheet_id)


def _get_sheet():
    """対象シートを取得。"""
    spreadsheet = _get_client()
    sheet_name = os.environ.get("SHEET_NAME", "todos")
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
