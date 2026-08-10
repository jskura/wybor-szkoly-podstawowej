"""Polish number, money, area, date and count formatting.

Nothing here reads the process locale. A machine with a different locale would
otherwise render a different number, and the difference is invisible in review.

**The separator.** D125 ratified one character for the thousands separator: the
no-break space, U+00A0, so a price never breaks across two lines. It lives in
``config/params.yml`` and arrives here as a constructor argument. The same
character separates a number from its unit, which is why the formatter joins
``142`` and ``zł/m²`` with it too — one ratified character, two purposes, no
second copy.
"""

from __future__ import annotations

import dataclasses
import datetime
from decimal import ROUND_HALF_UP, Decimal

GROUP = 3
EN_DASH = "–"
DECIMAL_SEPARATOR = ","

# How a source names itself in a quarter label. A source absent from the map
# keeps its own name, so an unlisted source is visible rather than silent.
SOURCE_LABELS: dict[str, str] = {"gus_bdl": "GUS"}


@dataclasses.dataclass(frozen=True)
class Formatter:
    """Every rendered number passes through one of these methods."""

    thousands_sep: str

    # --- numbers ----------------------------------------------------------

    def format_int(self, value: int) -> str:
        sign = "-" if value < 0 else ""
        digits = str(abs(int(value)))
        groups: list[str] = []
        while digits:
            groups.append(digits[-GROUP:])
            digits = digits[:-GROUP]
        return sign + self.thousands_sep.join(reversed(groups))

    def format_decimal(self, value: Decimal, places: int) -> str:
        quantized = Decimal(value).quantize(
            Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP
        )
        if places == 0:
            return self.format_int(int(quantized))
        whole, _, fraction = str(abs(quantized)).partition(".")
        sign = "-" if quantized < 0 else ""
        return sign + self.format_int(int(whole)) + DECIMAL_SEPARATOR + fraction

    def format_ratio(self, value: Decimal) -> str:
        """One decimal, never more. A ratio to four places invents precision."""
        return self.format_decimal(value, 1)

    def format_whole(self, value: Decimal) -> str:
        return self.format_int(
            int(Decimal(value).quantize(Decimal(1), rounding=ROUND_HALF_UP))
        )

    # --- units ------------------------------------------------------------

    def join_unit(self, rendered: str, unit: str) -> str:
        """Join a rendered number to its unit with the ratified separator."""
        return rendered + self.thousands_sep + unit

    def format_ppm2(self, value: Decimal) -> str:
        return self.join_unit(self.format_whole(value), "zł/m²")

    def format_pln(self, value: int) -> str:
        return self.join_unit(self.format_int(value), "zł")

    def format_area(self, value: int) -> str:
        return self.join_unit(self.format_int(value), "m²")

    def format_range(self, low: Decimal, high: Decimal) -> str:
        return self.format_whole(low) + EN_DASH + self.format_whole(high)

    # --- dates ------------------------------------------------------------

    def format_date(self, value: datetime.date) -> str:
        return f"{value.day:02d}.{value.month:02d}.{value.year:04d}"

    def format_quarter(self, year: int, quarter: int) -> str:
        return f"{year}Q{quarter}"

    def format_source_quarter(self, source: str, year: int, quarter: int) -> str:
        label = SOURCE_LABELS.get(source, source)
        return f"{label} {self.format_quarter(year, quarter)}"

    # --- counted nouns ----------------------------------------------------

    def format_days(self, days: int) -> str:
        """``1 dnia``, and ``dni`` for every other count."""
        noun = "dnia" if days == 1 else "dni"
        return f"{self.format_int(days)} {noun}"

    def format_offers(self, count: int) -> str:
        """``1 oferta``, ``2 oferty``, ``5 ofert`` — the Polish plural."""
        units = count % 10
        tens = (count // 10) % 10
        if count == 1:
            noun = "oferta"
        elif tens != 1 and units in (2, 3, 4):
            noun = "oferty"
        else:
            noun = "ofert"
        return f"{self.format_int(count)} {noun}"
