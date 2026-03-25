"""
Dashboard orchestration helpers kept separate from the Streamlit entry point.
"""

from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal

import pandas as pd

from src.data import (
    convert_to_usd,
    fetch_market_cap_async,
    fetch_stock_data_async,
    fetch_usd_rates_async,
    fetch_ytd_start_price,
)
from src.models import (
    DashboardPayload,
    DateRange,
    ErrorCode,
    FxRateWindow,
    OperationResult,
    SeriesPair,
    build_date_range,
    error_result,
    success_result,
)


async def fetch_dashboard_payload(
    sector_data: dict[str, str],
    requested_range: DateRange,
    include_usd: bool,
) -> DashboardPayload:
    """Fetch all remote data needed to render the dashboard."""

    tr_result_task = fetch_stock_data_async(
        sector_data["TR"],
        requested_range.start,
        requested_range.end,
        is_russian=False,
    )
    ru_result_task = fetch_stock_data_async(
        sector_data["RU"],
        requested_range.start,
        requested_range.end,
        is_russian=True,
    )
    tr_cap_task = fetch_market_cap_async(sector_data["TR"])
    ru_cap_task = fetch_market_cap_async(sector_data["RU"])
    tr_ytd_task = fetch_ytd_start_price(sector_data["TR"], requested_range.end, is_russian=False)
    ru_ytd_task = fetch_ytd_start_price(sector_data["RU"], requested_range.end, is_russian=True)

    if include_usd:
        start_year = date(requested_range.end.year, 1, 1)
        fx_start = min(requested_range.start, start_year)
        (
            tr_result,
            ru_result,
            tr_cap,
            ru_cap,
            tr_ytd_start,
            ru_ytd_start,
            usd_rates,
        ) = await asyncio.gather(
            tr_result_task,
            ru_result_task,
            tr_cap_task,
            ru_cap_task,
            tr_ytd_task,
            ru_ytd_task,
            fetch_usd_rates_async(fx_start, requested_range.end),
        )
    else:
        (
            tr_result,
            ru_result,
            tr_cap,
            ru_cap,
            tr_ytd_start,
            ru_ytd_start,
        ) = await asyncio.gather(
            tr_result_task,
            ru_result_task,
            tr_cap_task,
            ru_cap_task,
            tr_ytd_task,
            ru_ytd_task,
        )
        usd_rates = error_result("conversion_incomplete", requested_range)

    return DashboardPayload(
        tr_result=tr_result,
        ru_result=ru_result,
        tr_cap=tr_cap,
        ru_cap=ru_cap,
        tr_ytd_start=tr_ytd_start,
        ru_ytd_start=ru_ytd_start,
        usd_rates=usd_rates,
    )


def load_dashboard_data(
    sector_data: dict[str, str],
    start_date: date,
    end_date: date,
    include_usd: bool,
) -> DashboardPayload:
    """Run async data collection and normalize the result structure."""

    requested_range = build_date_range(start_date, end_date)
    try:
        return asyncio.run(
            fetch_dashboard_payload(sector_data, requested_range, include_usd)
        )
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                fetch_dashboard_payload(sector_data, requested_range, include_usd)
            )
        finally:
            loop.close()


def get_currency_labels(is_usd_conversion_active: bool) -> tuple[str, str, str]:
    """Return price labels for the current display mode."""

    if is_usd_conversion_active:
        return "$", "$", "USD"

    return "₺", "₽", ""


def calculate_ytd_change(
    price_result: OperationResult[pd.Series],
    baseline_result: OperationResult[Decimal],
) -> OperationResult[float]:
    """Calculate YTD change for the selected end-year."""

    requested_range = price_result.requested_range
    if not price_result.is_success or not baseline_result.is_success:
        return error_result("insufficient_data", requested_range)

    if price_result.payload is None or baseline_result.payload is None:
        return error_result("insufficient_data", requested_range)

    if (
        price_result.payload.empty
        or baseline_result.payload <= 0
        or not baseline_result.is_complete
    ):
        return error_result("insufficient_data", requested_range)

    current_price = Decimal(str(price_result.payload.iloc[-1]))
    change_pct = float(
        (current_price - baseline_result.payload) / baseline_result.payload * Decimal("100")
    )
    return success_result(
        change_pct,
        requested_range,
        price_result.effective_range,
        is_complete=price_result.is_complete and baseline_result.is_complete,
    )


def calculate_ytd_change_usd(
    price_result: OperationResult[pd.Series],
    baseline_result: OperationResult[Decimal],
    currency_code: str,
    fx_rates: FxRateWindow,
) -> OperationResult[float]:
    """Calculate YTD change using USD-converted prices.

    Converts the local-currency price series and baseline to USD before
    computing the percentage change.  Falls back to the local-currency
    calculation when USD conversion yields insufficient data.
    """

    requested_range = price_result.requested_range
    if not price_result.is_success or not baseline_result.is_success:
        return error_result("insufficient_data", requested_range)

    if price_result.payload is None or baseline_result.payload is None:
        return error_result("insufficient_data", requested_range)

    if (
        price_result.payload.empty
        or baseline_result.payload <= 0
        or not baseline_result.is_complete
    ):
        return error_result("insufficient_data", requested_range)

    # Convert the baseline amount into USD using the FX rate on the baseline date
    baseline_date = pd.Timestamp(baseline_result.effective_range.start)
    baseline_series = pd.Series([baseline_result.payload], index=[baseline_date])
    converted_baseline_series = convert_to_usd(baseline_series, currency_code, fx_rates)
    
    if converted_baseline_series.empty:
        # Fallback to local currency YTD
        return calculate_ytd_change(price_result, baseline_result)
        
    usd_baseline = converted_baseline_series.iloc[0]

    # Convert the full price series to USD
    usd_series = convert_to_usd(price_result.payload, currency_code, fx_rates)
    if usd_series.empty or len(usd_series) < 2:
        return calculate_ytd_change(price_result, baseline_result)

    usd_current = usd_series.iloc[-1]

    try:
        baseline_dec = Decimal(str(float(usd_baseline)))
        current_dec = Decimal(str(float(usd_current)))
    except Exception:
        return calculate_ytd_change(price_result, baseline_result)

    if baseline_dec <= 0:
        return calculate_ytd_change(price_result, baseline_result)

    change_pct = float(
        (current_dec - baseline_dec) / baseline_dec * Decimal("100")
    )
    return success_result(
        change_pct,
        requested_range,
        price_result.effective_range,
        is_complete=price_result.is_complete and baseline_result.is_complete,
    )


def prepare_comparison_series(
    tr_result: OperationResult[pd.Series],
    ru_result: OperationResult[pd.Series],
    usd_rates_result: OperationResult[FxRateWindow],
    show_usd: bool,
    min_points: int,
) -> OperationResult[SeriesPair]:
    """Prepare comparison series for render-time use."""

    requested_range = tr_result.requested_range or ru_result.requested_range
    if not tr_result.is_success or not ru_result.is_success:
        return error_result("insufficient_data", requested_range)

    if tr_result.payload is None or ru_result.payload is None:
        return error_result("insufficient_data", requested_range)

    if not show_usd:
        tr_currency, ru_currency, currency_label = get_currency_labels(False)
        return _build_series_pair_result(
            tr_result.payload,
            ru_result.payload,
            requested_range,
            min_points=min_points,
            tr_currency=tr_currency,
            ru_currency=ru_currency,
            currency_label=currency_label,
            error_code="insufficient_data",
        )

    if not usd_rates_result.is_success or usd_rates_result.payload is None:
        return error_result("conversion_incomplete", requested_range)

    converted_tr = convert_to_usd(tr_result.payload, "TRY", usd_rates_result.payload)
    converted_ru = convert_to_usd(ru_result.payload, "RUB", usd_rates_result.payload)
    tr_currency, ru_currency, currency_label = get_currency_labels(True)
    return _build_series_pair_result(
        converted_tr,
        converted_ru,
        requested_range,
        min_points=min_points,
        tr_currency=tr_currency,
        ru_currency=ru_currency,
        currency_label=currency_label,
        error_code="conversion_incomplete",
    )


def _build_effective_range_from_index(index: pd.Index) -> DateRange | None:
    """Build an effective date range from a pandas index."""

    if len(index) == 0:
        return None

    start = pd.Timestamp(index.min()).date()
    end = pd.Timestamp(index.max()).date()
    return build_date_range(start, end)


def _build_series_pair_result(
    tr_series: pd.Series,
    ru_series: pd.Series,
    requested_range: DateRange | None,
    *,
    min_points: int,
    tr_currency: str,
    ru_currency: str,
    currency_label: str,
    error_code: ErrorCode,
) -> OperationResult[SeriesPair]:
    """Align both series to the shared trading window before rendering."""

    aligned_df = pd.concat([tr_series.rename("tr"), ru_series.rename("ru")], axis=1)
    # Forward fill handles non-overlapping holidays organically (Outer Join)
    aligned_df = aligned_df.ffill().dropna()

    effective_range = _build_effective_range_from_index(aligned_df.index)
    if effective_range is None or len(aligned_df) < min_points:
        return error_result(
            error_code,
            requested_range,
            effective_range=effective_range,
        )

    return success_result(
        SeriesPair(
            tr_series=aligned_df["tr"],
            ru_series=aligned_df["ru"],
            tr_currency=tr_currency,
            ru_currency=ru_currency,
            currency_label=currency_label,
        ),
        requested_range,
        effective_range,
        is_complete=effective_range == requested_range,
    )
