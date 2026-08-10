"""The citation record, and the two refusals it makes.

The badge reads its act title and its pre-emption holder from here. No module in
this package holds either string, so a render helper cannot name the wrong
authority: it never holds an authority's name at all (F16).

**The first refusal.** A regime whose act title and holder nobody has ratified
does not render. `19` §2a marks all three forest claims `‡` unverified (D122),
so the forest badge is blocked. This mirrors the unit map, which refuses to serve
entries nobody has checked against the register.

**The second refusal.** D104 removed the expiry, so this file carries no
``expires_at``, no ``max_age_days`` and no equivalent. The loader rejects such a
key by name, which stops a quiet config addition from undoing the decision.
"""

from __future__ import annotations

import dataclasses
import datetime
import pathlib

import yaml

from .errors import BadgeCopyUnratified, CitationRecordError

# What a claim asserts. `identity` names the act or the authority; `threshold`
# carries a number or a date; `scope` states who or what the rule reaches.
CLAIM_KINDS: tuple[str, ...] = ("identity", "threshold", "scope")

BADGE_REGIMES: tuple[str, ...] = ("agricultural", "forest")

# D104 removed the staleness clock. These keys must never come back.
EXPIRY_KEYS: frozenset[str] = frozenset(
    {"expires_at", "expiry", "max_age_days", "citation_max_age_days"}
)

CLAIM_FIELDS: tuple[str, ...] = (
    "claim_id",
    "kind",
    "value",
    "source",
    "dziennik_ustaw_reference",
    "consolidated_text_id",
    "text_as_of",
    "source_url",
    "verified_at",
    "verified_by",
    "verification_note",
)

REGIME_FIELDS: tuple[str, ...] = (
    "regime",
    "act_title",
    "preemption_holder",
    "identity_ratified",
    "identity_source",
    "claims",
)


@dataclasses.dataclass(frozen=True)
class Claim:
    """One legal claim, with the state of the reading behind it."""

    claim_id: str
    kind: str
    value: str
    source: str
    dziennik_ustaw_reference: str
    consolidated_text_id: str
    text_as_of: datetime.date | None
    source_url: str
    verified_at: datetime.date | None
    verified_by: str | None
    verification_note: str


@dataclasses.dataclass(frozen=True)
class RegimeCitation:
    """Everything one badge may say, and the date somebody last checked it."""

    regime: str
    act_title: str
    preemption_holder: str
    identity_source: str
    claims: tuple[Claim, ...]

    @property
    def verified_at(self) -> datetime.date | None:
        """The most recent reading of this act, or ``None`` for none at all."""
        dates = [claim.verified_at for claim in self.claims if claim.verified_at]
        return max(dates) if dates else None

    @property
    def verified_thresholds(self) -> tuple[Claim, ...]:
        return tuple(
            claim
            for claim in self.claims
            if claim.kind == "threshold" and claim.verified_at is not None
        )


class CitationRecord:
    """A read-only lookup from a regime to what its badge may say."""

    def __init__(
        self,
        entries: dict[str, RegimeCitation],
        ratified: dict[str, bool],
        *,
        path: pathlib.Path,
    ) -> None:
        self._entries = dict(entries)
        self._ratified = dict(ratified)
        self._path = path

    @property
    def regimes(self) -> tuple[str, ...]:
        return tuple(self._entries)

    def is_ratified(self, regime: str) -> bool:
        return self._ratified[regime]

    def claims(self, regime: str) -> tuple[Claim, ...]:
        return self._entries[regime].claims

    def for_regime(self, regime: str) -> RegimeCitation:
        """The entry, or an error saying who has to read what.

        Raises ``BadgeCopyUnratified`` while the owner has not ratified the act
        title and the pre-emption holder.
        """
        try:
            entry = self._entries[regime]
        except KeyError as exc:
            raise CitationRecordError(
                f"{self._path} carries no entry for the regime {regime!r}"
            ) from exc
        if not self._ratified[regime]:
            raise BadgeCopyUnratified(
                f"the {regime} regime is not ratified in {self._path}. Its act "
                f"title and its pre-emption holder rest on {entry.identity_source}. "
                "Read the act, then set `identity_ratified: true` in the same "
                "commit. A badge naming the wrong authority is worse than none."
            )
        return entry


def _keys(node: object) -> list[str]:
    if isinstance(node, dict):
        found = list(node)
        for value in node.values():
            found.extend(_keys(value))
        return found
    if isinstance(node, list):
        found = []
        for value in node:
            found.extend(_keys(value))
        return found
    return []


def _as_date(value: object, path: pathlib.Path, field: str) -> datetime.date | None:
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value)
        except ValueError as exc:
            raise CitationRecordError(
                f"{path}: {field} is {value!r}, which is not a date"
            ) from exc
    raise CitationRecordError(f"{path}: {field} is not a date")


def _claim(entry: dict, path: pathlib.Path) -> Claim:
    missing = [field for field in CLAIM_FIELDS if field not in entry]
    if missing:
        raise CitationRecordError(
            f"{path}: the claim {entry.get('claim_id')!r} lacks {missing[0]}"
        )
    if entry["kind"] not in CLAIM_KINDS:
        raise CitationRecordError(
            f"{path}: the claim {entry['claim_id']!r} declares the kind "
            f"{entry['kind']!r}, which is outside {CLAIM_KINDS}"
        )
    verified_at = _as_date(entry["verified_at"], path, "verified_at")
    text_as_of = _as_date(entry["text_as_of"], path, "text_as_of")
    if verified_at and text_as_of and verified_at < text_as_of:
        raise CitationRecordError(
            f"{path}: the claim {entry['claim_id']!r} records a verification on "
            f"{verified_at} against a text of {text_as_of}. A reading of an "
            "older text proves nothing about this one."
        )
    return Claim(
        claim_id=entry["claim_id"],
        kind=entry["kind"],
        value=entry["value"],
        source=entry["source"],
        dziennik_ustaw_reference=entry["dziennik_ustaw_reference"],
        consolidated_text_id=entry["consolidated_text_id"],
        text_as_of=text_as_of,
        source_url=entry["source_url"],
        verified_at=verified_at,
        verified_by=entry["verified_by"],
        verification_note=entry["verification_note"],
    )


def load_citations(path: pathlib.Path | str) -> CitationRecord:
    """Read the record from ``path``."""
    path = pathlib.Path(path)
    if not path.exists():
        raise CitationRecordError(f"{path} is missing. The record is committed.")

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise CitationRecordError(f"{path} is not valid YAML: {exc}") from exc

    reintroduced = sorted(set(_keys(raw)) & EXPIRY_KEYS)
    if reintroduced:
        raise CitationRecordError(
            f"{path} carries the key {reintroduced[0]!r}. D104 removed the "
            "expiry, because the clock measured our reading habits and not the "
            "law. D105 prompts on the first badge of a session instead."
        )

    entries = raw.get("regimes")
    if not isinstance(entries, list) or entries == []:
        raise CitationRecordError(f"{path}: `regimes` must be a non-empty list")

    found: dict[str, RegimeCitation] = {}
    ratified: dict[str, bool] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise CitationRecordError(f"{path}: every regime must be a mapping")
        missing = [field for field in REGIME_FIELDS if field not in entry]
        if missing:
            raise CitationRecordError(
                f"{path}: the regime {entry.get('regime')!r} lacks {missing[0]}"
            )
        regime = entry["regime"]
        if regime not in BADGE_REGIMES:
            raise CitationRecordError(
                f"{path}: the regime {regime!r} is outside {BADGE_REGIMES}. An "
                "entry with no regime cannot be routed to a badge."
            )
        if regime in found:
            raise CitationRecordError(f"{path}: the regime {regime!r} appears twice")
        claims = entry["claims"]
        if not isinstance(claims, list) or claims == []:
            raise CitationRecordError(
                f"{path}: the regime {regime!r} states no claim at all"
            )
        found[regime] = RegimeCitation(
            regime=regime,
            act_title=entry["act_title"],
            preemption_holder=entry["preemption_holder"],
            identity_source=entry["identity_source"],
            claims=tuple(_claim(claim, path) for claim in claims),
        )
        ratified[regime] = bool(entry["identity_ratified"])

    return CitationRecord(found, ratified, path=path)
