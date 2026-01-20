"""Support assistant data entries."""

from support_assistant.data.faq import FAQ_ENTRIES, find_faq_topic
from support_assistant.data.intents import INTENT_KEYWORDS, INTENT_PRIORITY

__all__ = [
    "FAQ_ENTRIES",
    "find_faq_topic",
    "INTENT_KEYWORDS",
    "INTENT_PRIORITY",
]
