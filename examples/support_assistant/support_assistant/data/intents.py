"""Hard-coded intent keyword mappings."""

INTENT_KEYWORDS: dict[str, list[str]] = {
    "handoff": ["human", "agent", "担当者", "オペレーター", "人に", "問い合わせ"],
    "create_ticket": ["チケット", "サポート", "issue", "problem", "助けて"],
    "faq": ["パスワード", "請求", "起動", "reset", "billing", "crash"],
}

INTENT_PRIORITY = ["handoff", "create_ticket", "faq"]
