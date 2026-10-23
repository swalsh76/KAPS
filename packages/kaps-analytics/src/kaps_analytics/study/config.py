"""The study's settings. They are part of the pre-registration: a change changes its digest."""

import hashlib
import json
from dataclasses import asdict, dataclass

CENT_E6 = 10_000
DEFAULT_PRICE_EDGES_E6 = tuple(
    cents * CENT_E6 for cents in (0, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100)
)
# a trade's yes price is 1 cent to 99 cents, so the last band is closed at a dollar
DEFAULT_TLEFT_EDGES_S = (0, 600, 3_600, 21_600, 86_400, 259_200, 604_800, 2_592_000)
DEFAULT_REFERENCE = ("expected_expiration_time", "close_time")  # D10


@dataclass(frozen=True, slots=True)
class StudyConfig:
    """Price bands (yes price, millionths of a dollar, upper edge exclusive), time-to-expiry bands
    (seconds), the split (D12), the time reference per category (D10) and the verdict rules."""

    price_edges_e6: tuple[int, ...] = DEFAULT_PRICE_EDGES_E6
    tleft_edges_s: tuple[int, ...] = DEFAULT_TLEFT_EDGES_S
    fractions: tuple[float, float, float] = (0.70, 0.15, 0.15)
    reference_by_category: tuple[tuple[str, tuple[str, ...]], ...] = ()
    resamples: int = 10_000
    seed: int = 20_261_023
    min_events: int = 300  # independent events a segment needs for a GO
    max_segments: int = 12  # D11
    family_alpha: float = 0.025  # one-sided; a segment is tested at family_alpha / segments
    verdict_maker_share_e2: int = 50  # D13: the conservative maker share, in hundredths

    def __post_init__(self) -> None:
        if abs(sum(self.fractions) - 1.0) > 1e-9 or min(self.fractions) <= 0:
            raise ValueError("the split fractions must be positive and sum to one")
        for edges in (self.price_edges_e6, self.tleft_edges_s):
            if len(edges) < 2 or list(edges) != sorted(set(edges)):
                raise ValueError("band edges must be strictly increasing, at least two")
        if self.price_edges_e6[0] != 0 or self.price_edges_e6[-1] != 1_000_000:
            raise ValueError("price bands must cover 0 to one dollar")
        if self.tleft_edges_s[0] != 0:
            raise ValueError("time bands must start at zero")
        if not 0 <= self.verdict_maker_share_e2 <= 100:
            raise ValueError("the maker share is within 0 to 100 hundredths")

    def reference_for(self, category: str) -> tuple[str, ...]:
        """The market time fields tried in order for a category's time to expiry."""
        return dict(self.reference_by_category).get(category, DEFAULT_REFERENCE)

    def digest(self) -> str:
        """A stable hash of every setting (the verdict-relevant ones), for the pre-registration."""
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()
