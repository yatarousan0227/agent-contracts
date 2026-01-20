"""Knowledge base modules for tech support."""

from examples.interactive_tech_support.knowledge.hardware_kb import HARDWARE_KB
from examples.interactive_tech_support.knowledge.software_kb import SOFTWARE_KB
from examples.interactive_tech_support.knowledge.network_kb import NETWORK_KB
from examples.interactive_tech_support.knowledge.faq_data import FAQ_DATA

# Japanese knowledge bases
from examples.interactive_tech_support.knowledge.hardware_kb_ja import HARDWARE_KB_JA
from examples.interactive_tech_support.knowledge.software_kb_ja import SOFTWARE_KB_JA
from examples.interactive_tech_support.knowledge.network_kb_ja import NETWORK_KB_JA
from examples.interactive_tech_support.knowledge.faq_data_ja import FAQ_DATA_JA

__all__ = [
    "HARDWARE_KB",
    "SOFTWARE_KB",
    "NETWORK_KB",
    "FAQ_DATA",
    # Japanese knowledge bases
    "HARDWARE_KB_JA",
    "SOFTWARE_KB_JA",
    "NETWORK_KB_JA",
    "FAQ_DATA_JA",
]
