"""Named identities for the six division leads and the supreme boss
overseeing all of them -- a personality/branding layer, decided with
Mohamed 2026-08-10. Real human names, his choice.

Generic shared infra, not division-specific -- the single source of
truth any interface can pull a name from, rather than each caller
hardcoding its own copy.

Learning shares Personal & Education's name (Sumaya) -- it's its own
Telegram bot/server for practical reasons (see ARCHITECTURE.md's
division-server port table), but the same division conceptually as
"6 divisions" describes it.
"""

DIVISION_NAMES = {
    "fixera": "Mahir",
    "forex": "Abdisalam",
    "personal": "Sumaya",
    "learning": "Sumaya",
    "rii": "Zainab",
    "audit": "Huda",
    "systems": "Abdullahi",
}

SUPREME_BOSS = "Abdi"
SUPREME_BOSS_NICKNAME = "Loverboy"  # Mohamed's own nickname for Abdi, 2026-08-10


def name_for(division: str) -> str:
    """Falls back to the supreme boss's name for an unknown division
    key, rather than raising -- there's always someone to attribute a
    reply to."""
    return DIVISION_NAMES.get(division, SUPREME_BOSS)
