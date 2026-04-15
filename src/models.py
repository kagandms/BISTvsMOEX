"""
Typed result models shared across the dashboard.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Generic, Literal, TypeVar

import pandas as pd

ResultStatus = Literal["success", "error"]
AnalysisMode = Literal["local", "usd", "real"]
ErrorCode = Literal[
    "timeout",
    "connection",
    "schema_error",
    "no_data",
    "insufficient_data",
    "conversion_incomplete",
    "inflation_incomplete",
    "unsupported_window",
]

PayloadT = TypeVar("PayloadT")


@dataclass(frozen=True)
class DateRange:
    """Inclusive date range used by the dashboard."""

    start: date
    end: date


@dataclass(frozen=True)
class OperationResult(Generic[PayloadT]):
    """Standard operation result contract used across the app."""

    status: ResultStatus
    error_code: ErrorCode | None
    requested_range: DateRange | None
    effective_range: DateRange | None
    is_complete: bool
    payload: PayloadT | None

    @property
    def is_success(self) -> bool:
        """Return True when the operation completed with a payload."""

        return self.status == "success" and self.payload is not None


@dataclass(frozen=True)
class FxRateWindow:
    """FX rate payload used for USD conversion."""

    usd_try: pd.DataFrame | None
    usd_rub: pd.DataFrame | None


@dataclass(frozen=True)
class InflationWindow:
    """Monthly CPI index payload used for real-return conversion."""

    tr_cpi: pd.Series
    ru_cpi: pd.Series
    shared_base_month: pd.Timestamp


@dataclass(frozen=True)
class SeriesPair:
    """Prepared comparison series ready for UI rendering."""

    tr_series: pd.Series
    ru_series: pd.Series
    tr_currency: str
    ru_currency: str
    currency_label: str


@dataclass(frozen=True)
class DashboardPayload:
    """Fetched dashboard inputs before render-time transformation."""

    tr_result: OperationResult[pd.Series]
    ru_result: OperationResult[pd.Series]
    tr_cap: OperationResult[float]
    ru_cap: OperationResult[float]
    tr_ytd_start: OperationResult[Decimal]
    ru_ytd_start: OperationResult[Decimal]
    usd_rates: OperationResult[FxRateWindow]
    inflation_window: OperationResult[InflationWindow]


def build_date_range(start: date, end: date) -> DateRange:
    """Build a normalized inclusive date range."""

    return DateRange(start=start, end=end)


def success_result(
    payload: PayloadT,
    requested_range: DateRange | None,
    effective_range: DateRange | None,
    *,
    is_complete: bool = True,
) -> OperationResult[PayloadT]:
    """Create a successful operation result."""

    return OperationResult(
        status="success",
        error_code=None,
        requested_range=requested_range,
        effective_range=effective_range,
        is_complete=is_complete,
        payload=payload,
    )


def error_result(
    error_code: ErrorCode,
    requested_range: DateRange | None,
    *,
    effective_range: DateRange | None = None,
) -> OperationResult[PayloadT]:
    """Create a failed operation result."""

    return OperationResult(
        status="error",
        error_code=error_code,
        requested_range=requested_range,
        effective_range=effective_range,
        is_complete=False,
        payload=None,
    )
