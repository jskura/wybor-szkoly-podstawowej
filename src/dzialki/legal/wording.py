"""Every string either badge can show, and nothing else.

One constant per line, each hashed by a test, so an edit shows up as a changed
hash rather than as a silent rewrite.

**What is not here.** No act title, no pre-emption holder, no threshold and no
date. Lines 2 and 3 are templates, and the citation record fills them. That is
what makes the wrong-authority failure unwritable rather than merely tested.

The farmland copy comes from `19` §2.2, which the owner ratified. The forest copy
comes from `19` §2a.2, which nobody has ratified yet. The two preemption lines
differ in shape because the ratified farmland line carries no brackets and the
proposed forest line does; the test plan hashes both, so neither may drift.
"""

from __future__ import annotations

from types import MappingProxyType

# Line 1, by regime. U+26A0 WARNING SIGN, U+2014 EM DASH, and the area formatted
# by the one declared formatter, which reads its separator from config.
TITLE_TEMPLATES = MappingProxyType(
    {
        "agricultural": "⚠ Grunt rolny — {area} m²",
        "forest": "⚠ Grunt leśny — {area} m²",
    }
)

# Line 2. One template for both regimes: the sentence is identical and only the
# act differs, so a second copy could only drift.
RESTRICTION_TEMPLATE = "Możliwe ograniczenia w nabyciu ({act_title})"

# Line 3, by regime.
PREEMPTION_TEMPLATES = MappingProxyType(
    {
        "agricultural": "Możliwe prawo pierwokupu {holder}",
        "forest": "Możliwe prawo pierwokupu ({holder})",
    }
)

# Line 4. The advice is identical for both regimes, so it is one object. A test
# asserts identity, not equality, so nobody can fork it and soften one copy.
BADGE_NOTARY_LINE = "sprawdź u notariusza przed ofertą"
NOTARY_LINE_PREFIX = "→ "
NOTARY_LINE = NOTARY_LINE_PREFIX + BADGE_NOTARY_LINE

# The unknown class. Silence is not a clean bill of health, so the page says what
# it does not know (`19` §2.2).
UNKNOWN_CLASS_STATEMENT = (
    "klasa użytku nieznana — nie wiemy, czy obowiązują ograniczenia"
)

# The operator's task, shown on the first badge of a regime in a session (D105,
# D116). It names the act to check and the date somebody last checked it.
REVERIFY_PROMPT_TEMPLATE = (
    "Przepisy mogły się zmienić — sprawdź {act_title}; "
    "ostatnia weryfikacja {verified_at}"
)
NEVER_VERIFIED = "nigdy"

# The alarm code for a symbol the table does not carry (FR-49). It is addressed
# to the operator and never reaches the page.
UNRECOGNISED_CLASS_ALARM = "register_class_unrecognised"
