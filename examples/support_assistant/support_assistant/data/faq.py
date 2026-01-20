"""Hard-coded FAQ entries for the support assistant."""

FAQ_ENTRIES: dict[str, dict[str, object]] = {
    "password_reset": {
        "question": "パスワードをリセットするには？",
        "answer": "ログイン画面の『パスワードを忘れた場合』から再設定できます。",
        "keywords": ["パスワード", "リセット", "忘れた", "password", "reset"],
    },
    "billing": {
        "question": "請求書や支払い方法を確認したい",
        "answer": "アカウント設定の『請求』から請求書の確認と支払い方法の変更ができます。",
        "keywords": ["請求", "支払い", "billing", "invoice"],
    },
    "troubleshooting": {
        "question": "アプリが起動しません",
        "answer": "最新版への更新後、端末を再起動してから再度お試しください。",
        "keywords": ["起動", "クラッシュ", "動かない", "crash", "launch"],
    },
}


def find_faq_topic(message: str) -> str | None:
    """Return matching FAQ topic key for a message."""
    lowered = message.lower()
    for topic, entry in FAQ_ENTRIES.items():
        for keyword in entry.get("keywords", []):
            if keyword.lower() in lowered:
                return topic
    return None
