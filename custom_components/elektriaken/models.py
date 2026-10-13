"""Data types used by Elektriaken."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class PricePeriod:
    """A market price period, stored without VAT in EUR/MWh."""

    start: datetime
    end: datetime
    price: float

    @property
    def minutes(self) -> int:
        """Return the UTC duration in whole minutes."""
        return int((self.end - self.start).total_seconds() // 60)


@dataclass(frozen=True, slots=True)
class BestWindow:
    """A contiguous cheapest window."""

    start: datetime
    end: datetime
    duration_minutes: int
    average_raw: float
    starting_now_average_raw: float | None
