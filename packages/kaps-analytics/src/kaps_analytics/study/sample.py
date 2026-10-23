"""Sampling by event (D16): every trade of a hash-chosen share of the events.

The run cannot hold every trade in memory, and thinning trades would break the events apart.
Choosing whole events keeps the events independent, so the clustered intervals stay valid; only
their number, and so the power, falls. The choice is a hash of the seed and the event ticker, taken
with ``hashlib`` and not polars' own hash, which is not promised to be stable between versions.
"""

import hashlib
from collections.abc import Iterable

DEFAULT_CEILING = 40_000_000  # trades loaded at once: about 18 GB of the analytics node's 36 GB
_MIN_SHARE = 0.0001


def event_fraction(event: str, seed: int) -> float:
    """A fixed number in [0, 1) for this event under this seed."""
    digest = hashlib.blake2b(f"{seed}:{event}".encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big") / 2**64


def chosen_events(events: Iterable[str], share: float, seed: int) -> list[str]:
    """The events whose fraction falls below ``share``, in the order given."""
    if share >= 1.0:
        return list(events)
    return [event for event in events if event_fraction(event, seed) < share]


def share_for(trades: int, ceiling: int = DEFAULT_CEILING) -> float:
    """The largest share, to four decimals, that keeps about ``ceiling`` trades or fewer."""
    if trades <= ceiling:
        return 1.0
    return max(_MIN_SHARE, int(ceiling / trades * 10_000) / 10_000)
