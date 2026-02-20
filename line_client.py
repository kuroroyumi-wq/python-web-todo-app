"""LINE Messaging API Push通知クライアント。"""
import logging
import os

import requests

logger = logging.getLogger(__name__)


def send_push_message(text: str) -> bool:
    """LINE Push API でテキストメッセージを送信。成功時 True。"""
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
    user_id = os.environ.get("LINE_USER_ID", "").strip()

    if not token:
        logger.error("LINE_CHANNEL_ACCESS_TOKEN が未設定です")
        return False
    if not user_id:
        logger.error("LINE_USER_ID が未設定です")
        return False

    try:
        resp = requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            json={
                "to": user_id,
                "messages": [{"type": "text", "text": text}],
            },
            timeout=10,
        )
    except requests.RequestException as e:
        logger.error("LINE Push送信中に例外: %s", e)
        return False

    if resp.status_code == 200:
        return True

    logger.error("LINE Push送信失敗: status=%d", resp.status_code)
    return False
