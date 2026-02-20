"""
GoogleスプレッドシートをTodoの永続化先として利用するクライアントモジュール。
責務: Sheets APIとの通信、CRUD操作のみ。
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import google.auth
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = [
    "id", "title", "description", "priority", "status",
    "due_at", "created_at", "updated_at", "done_at", "last_reminded_at",
]

_OLD_TO_NEW = {"body": "description", "due_date": "due_at"}

VALID_PRIORITIES = {"High", "Medium", "Low"}
VALID_STATUSES = {"open", "done"}


# ── Timezone helpers ─────────────────────────────────────────────────

def _get_tz() -> ZoneInfo:
    name = os.environ.get("APP_TIMEZONE", "Asia/Tokyo").strip()
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("Asia/Tokyo")


def _now_iso() -> str:
    return datetime.now(_get_tz()).isoformat()


def _parse_iso(value: str) -> datetime | None:
    if not value or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip())
    except ValueError:
        return None


# ── Google Auth ──────────────────────────────────────────────────────

def _get_google_credentials():
    """
    Google 認証情報を取得。
    優先順位: 1) JSON_PATH  2) JSON文字列  3) ADC (Cloud Run SA)
    """
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
            raise RuntimeError(
                "GOOGLE_SERVICE_ACCOUNT_JSON が空です。正しいJSON文字列を設定してください。"
            )
        try:
            info = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"GOOGLE_SERVICE_ACCOUNT_JSON のJSON解析に失敗しました: {e}. "
                "JSONは1行（minify）で貼り付けてください。"
            )
        return Credentials.from_service_account_info(info, scopes=SCOPES)

    try:
        creds, _project_id = google.auth.default(scopes=SCOPES)
    except Exception as e:
        raise RuntimeError(
            "Google 認証情報を取得できませんでした。"
            "Cloud Run を使う場合は、Cloud Run サービスにサービスアカウントを割り当ててください。"
            "または GOOGLE_SERVICE_ACCOUNT_JSON(_PATH) を設定してください。"
            f"（詳細: {e}）"
        )

    if getattr(creds, "requires_scopes", False) and hasattr(creds, "with_scopes"):
        creds = creds.with_scopes(SCOPES)
    return creds


# ── Sheet access ─────────────────────────────────────────────────────

def _get_client():
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
    spreadsheet = _get_client()
    sheet_name = os.environ.get("SHEET_NAME", "todos").strip() or "todos"
    return spreadsheet.worksheet(sheet_name)


# ── Header / Migration ──────────────────────────────────────────────

def get_header_map(worksheet) -> dict[str, int]:
    """ヘッダ行を読み取り {列名: 0-based index} を返す。"""
    return {h: i for i, h in enumerate(worksheet.row_values(1)) if h}


def _col_letter(index: int) -> str:
    return chr(ord("A") + index)


def _ensure_headers(worksheet) -> None:
    """ヘッダ行が新フォーマットであることを保証。旧形式なら自動マイグレーション。"""
    try:
        current = worksheet.row_values(1)
    except Exception:
        current = []

    if current == HEADERS:
        return

    needs_migration = (
        current
        and len(current) >= 1
        and current[0] == "id"
        and any(old in current for old in _OLD_TO_NEW)
    )

    if needs_migration:
        all_values = worksheet.get_all_values()
        old_headers = all_values[0]
        data_rows = all_values[1:]
        old_idx = {h: i for i, h in enumerate(old_headers)}

        migrated = []
        for row in data_rows:
            new_row = []
            for h in HEADERS:
                old_name = next(
                    (ok for ok, nk in _OLD_TO_NEW.items() if nk == h), None
                )
                if old_name and old_name in old_idx:
                    i = old_idx[old_name]
                    new_row.append(row[i] if i < len(row) else "")
                elif h in old_idx:
                    i = old_idx[h]
                    new_row.append(row[i] if i < len(row) else "")
                elif h == "priority":
                    new_row.append("Medium")
                elif h == "status":
                    new_row.append("open")
                else:
                    new_row.append("")
            migrated.append(new_row)

        worksheet.clear()
        end_col = _col_letter(len(HEADERS) - 1)
        worksheet.update(
            f"A1:{end_col}{1 + len(migrated)}",
            [HEADERS] + migrated,
            value_input_option="USER_ENTERED",
        )
        return

    end_col = _col_letter(len(HEADERS) - 1)
    worksheet.update(
        f"A1:{end_col}1", [HEADERS], value_input_option="USER_ENTERED"
    )


# ── Row helpers ──────────────────────────────────────────────────────

def _row_to_dict(row: list, hmap: dict[str, int]) -> dict:
    return {h: (row[i] if i < len(row) else "") for h, i in hmap.items()}


def _dict_to_row(data: dict) -> list:
    return [str(data.get(h, "")) for h in HEADERS]


# ── CRUD ─────────────────────────────────────────────────────────────

def fetch_all_todos() -> list[dict]:
    """全Todoを取得。ヘッダ行を動的解決してdict一覧で返す。"""
    sheet = _get_sheet()
    _ensure_headers(sheet)
    hmap = get_header_map(sheet)
    rows = sheet.get_all_values()
    id_col = hmap.get("id", 0)
    return [
        _row_to_dict(row, hmap)
        for row in rows[1:]
        if row and len(row) > id_col and row[id_col]
    ]


def fetch_todo_by_id(todo_id: str) -> dict | None:
    """指定IDのTodoを1件取得。見つからなければ None。"""
    sheet = _get_sheet()
    _ensure_headers(sheet)
    hmap = get_header_map(sheet)
    rows = sheet.get_all_values()
    id_col = hmap.get("id", 0)
    for row in rows[1:]:
        if len(row) > id_col and row[id_col] == todo_id:
            return _row_to_dict(row, hmap)
    return None


def create_todo(
    title: str,
    description: str = "",
    priority: str = "Medium",
    due_at: str = "",
) -> None:
    """新規Todoを1件登録。status は常に "open" で作成。"""
    sheet = _get_sheet()
    _ensure_headers(sheet)
    now = _now_iso()
    data = {
        "id": str(uuid.uuid4()),
        "title": title,
        "description": description,
        "priority": priority if priority in VALID_PRIORITIES else "Medium",
        "status": "open",
        "due_at": due_at,
        "created_at": now,
        "updated_at": now,
        "done_at": "",
        "last_reminded_at": "",
    }
    sheet.append_row(_dict_to_row(data), value_input_option="USER_ENTERED")


def update_todo(
    todo_id: str,
    title: str,
    description: str = "",
    priority: str = "Medium",
    due_at: str = "",
) -> None:
    """指定IDのTodoを更新。status / done_at / last_reminded_at は既存値を維持。"""
    sheet = _get_sheet()
    _ensure_headers(sheet)
    hmap = get_header_map(sheet)
    rows = sheet.get_all_values()
    id_col = hmap.get("id", 0)

    for row_num, row in enumerate(rows[1:], start=2):
        if len(row) > id_col and row[id_col] == todo_id:
            old = _row_to_dict(row, hmap)
            data = {
                "id": todo_id,
                "title": title,
                "description": description,
                "priority": priority if priority in VALID_PRIORITIES else "Medium",
                "status": old.get("status", "open"),
                "due_at": due_at,
                "created_at": old.get("created_at", ""),
                "updated_at": _now_iso(),
                "done_at": old.get("done_at", ""),
                "last_reminded_at": old.get("last_reminded_at", ""),
            }
            end_col = _col_letter(len(HEADERS) - 1)
            sheet.update(
                f"A{row_num}:{end_col}{row_num}",
                [_dict_to_row(data)],
                value_input_option="USER_ENTERED",
            )
            return


def toggle_status(todo_id: str) -> str | None:
    """open↔done を切り替え。新しい status を返す。対象なければ None。"""
    sheet = _get_sheet()
    _ensure_headers(sheet)
    hmap = get_header_map(sheet)
    rows = sheet.get_all_values()
    id_col = hmap.get("id", 0)

    for row_num, row in enumerate(rows[1:], start=2):
        if len(row) > id_col and row[id_col] == todo_id:
            old = _row_to_dict(row, hmap)
            now = _now_iso()
            new_status = "done" if old.get("status") != "done" else "open"
            data = {
                **old,
                "status": new_status,
                "done_at": now if new_status == "done" else "",
                "updated_at": now,
            }
            end_col = _col_letter(len(HEADERS) - 1)
            sheet.update(
                f"A{row_num}:{end_col}{row_num}",
                [_dict_to_row(data)],
                value_input_option="USER_ENTERED",
            )
            return new_status
    return None


def find_due_within(hours: int = 24) -> list[dict]:
    """status=open & due_at が now〜now+hours 以内のTodoを抽出（重複通知抑制つき）。"""
    todos = fetch_all_todos()
    tz = _get_tz()
    now = datetime.now(tz)
    window_end = now + timedelta(hours=hours)
    result = []

    for t in todos:
        if t.get("status") != "open":
            continue
        due = _parse_iso(t.get("due_at", ""))
        if due is None:
            continue
        if due.tzinfo is None:
            due = due.replace(tzinfo=tz)
        if not (now <= due <= window_end):
            continue
        last = _parse_iso(t.get("last_reminded_at", ""))
        if last is not None:
            if last.tzinfo is None:
                last = last.replace(tzinfo=tz)
            if (now - last).total_seconds() < hours * 3600:
                continue
        result.append(t)

    return result


def mark_reminded(todo_ids: list[str], reminded_at: str = "") -> None:
    """指定IDの last_reminded_at を一括更新。"""
    if not todo_ids:
        return
    if not reminded_at:
        reminded_at = _now_iso()

    sheet = _get_sheet()
    _ensure_headers(sheet)
    hmap = get_header_map(sheet)
    rows = sheet.get_all_values()
    id_col = hmap.get("id", 0)
    reminded_col = hmap.get("last_reminded_at")
    if reminded_col is None:
        return

    id_set = set(todo_ids)
    cells = []
    for row_num, row in enumerate(rows[1:], start=2):
        if len(row) > id_col and row[id_col] in id_set:
            cells.append(
                gspread.Cell(row=row_num, col=reminded_col + 1, value=reminded_at)
            )

    if cells:
        sheet.update_cells(cells, value_input_option="USER_ENTERED")
