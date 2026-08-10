"""The re-verification prompt (FR-74, V64, D104, D105, D116).

D104 removed the expiry. A clock on our own reading habits never told us the law
had changed, and no window length was defensible. D105 puts the check where the
risk is: the first badge of a regime in a session asks the operator to read that
regime's act.

The prompt is a task, never a gate. The badge renders whether the prompt appears,
is dismissed, or is never shown. A gate would rebuild the expiry D104 removed.

D116 makes it once per regime. Two farmland badges give one prompt. A farmland
badge and then a forest badge give two, each naming its own act, because the two
acts change independently.
"""

from __future__ import annotations

from dzialki.render import Formatter

from .citations import RegimeCitation
from .wording import NEVER_VERIFIED, REVERIFY_PROMPT_TEMPLATE


class ReverificationSession:
    """One reader's session. The counter lives here and nowhere else.

    Not a module global and not a file. A global would make the second session
    silent, and the operator who opens the application tomorrow is the one the
    prompt is for.
    """

    def __init__(self, *, formatter: Formatter) -> None:
        self._formatter = formatter
        self._prompted: set[str] = set()

    @property
    def prompted_regimes(self) -> frozenset[str]:
        return frozenset(self._prompted)

    def prompt_for(self, citation: RegimeCitation) -> str | None:
        """The prompt on the first badge of this regime, then ``None``.

        A prompt on every badge trains the reader to dismiss it, which is how a
        real change slips through.
        """
        if citation.regime in self._prompted:
            return None
        self._prompted.add(citation.regime)
        verified_at = citation.verified_at
        rendered = (
            NEVER_VERIFIED
            if verified_at is None
            else self._formatter.format_date(verified_at)
        )
        return REVERIFY_PROMPT_TEMPLATE.format(
            act_title=citation.act_title, verified_at=rendered
        )
