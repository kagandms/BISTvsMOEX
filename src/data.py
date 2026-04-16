"""
Data fetching module for The Eurasian Bridge application.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

import pandas as pd
import requests
import streamlit as st
import yfinance as yf
from curl_cffi import requests as curl_requests
from yfinance.exceptions import YFPricesMissingError, YFRateLimitError, YFTzMissingError

from src.config import API_CONFIG, CACHE_CONFIG, DATA_CONFIG, INFLATION_CONFIG, MARKET_CAPS
from src.exceptions import DataSourceError, UpstreamConnectionError, UpstreamTimeoutError
from src.models import (
    DateRange,
    FxRateWindow,
    InflationWindow,
    OperationResult,
    build_date_range,
    error_result,
    success_result,
)

logger = logging.getLogger(__name__)

_MOEX_ISS_CANDLES_URL = (
    "{base}/iss/engines/stock/markets/shares/boards/TQBR"
    "/securities/{ticker}/candles.json"
    "?interval=24&from={from_date}&till={till_date}&start={offset}"
)
_MOEX_ISS_PAGE_SIZE = 500
_MOEX_ISS_MAX_PAGES = 20  # Safety limit: 20 pages × 500 rows = 10,000 trading days (~40 years)

_moex_session: requests.Session | None = None
_session_lock = threading.Lock()


def _get_moex_session() -> requests.Session:
    """Return a reusable requests.Session for MOEX ISS calls (connection pooling)."""
    global _moex_session
    if _moex_session is None:
        with _session_lock:
            if _moex_session is None:
                _moex_session = requests.Session()
                _moex_session.headers.update(
                    {"User-Agent": "Mozilla/5.0 (compatible; EurasianBridge/1.0)"}
                )
    return _moex_session


def _build_requested_range(start_date: date, end_date: date) -> DateRange:
    """Create the requested date range."""

    return build_date_range(start_date, end_date)


def _validate_requested_window(start_date: date, end_date: date) -> DateRange | None:
    """Validate the requested date range."""

    if start_date >= end_date:
        return None

    return _build_requested_range(start_date, end_date)


def _sanitize_close_series(data_frame: pd.DataFrame) -> pd.Series:
    """Return a numeric close series with non-finite values removed."""

    if "Close" not in data_frame.columns:
        raise DataSourceError(
            "Upstream response is missing the Close column",
            error_code="schema_error",
        )

    close_series = pd.to_numeric(data_frame["Close"], errors="coerce")
    clean_series = close_series.replace([float("inf"), float("-inf")], pd.NA).dropna()
    clean_series.index = _strip_timezone(pd.to_datetime(clean_series.index))
    clean_series = clean_series[~clean_series.index.duplicated(keep="last")]
    clean_series = clean_series.sort_index()
    return clean_series


def _sanitize_numeric_series(series: pd.Series) -> pd.Series:
    """Return a numeric, finite, ordered series."""

    numeric_series = pd.to_numeric(series, errors="coerce")
    clean_series = numeric_series.replace([float("inf"), float("-inf")], pd.NA).dropna()
    clean_series.index = _strip_timezone(pd.to_datetime(clean_series.index))
    clean_series = clean_series[~clean_series.index.duplicated(keep="last")]
    return clean_series.sort_index()


def _build_effective_range(series: pd.Series) -> DateRange:
    """Build the effective range from a series index."""

    start = pd.Timestamp(series.index.min()).date()
    end = pd.Timestamp(series.index.max()).date()
    return build_date_range(start, end)


def _strip_timezone(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Return a timezone-naive datetime index."""

    if index.tz is None:
        return index

    return index.tz_localize(None)


def _build_price_success(
    series: pd.Series,
    requested_range: DateRange,
) -> OperationResult[pd.Series]:
    """Build a successful price-series result."""

    effective_range = _build_effective_range(series)
    is_complete = effective_range.end >= requested_range.end
    return success_result(
        series,
        requested_range,
        effective_range,
        is_complete=is_complete,
    )


def _fetch_yfinance_history(
    ticker: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Fetch raw Yahoo Finance history with native request timeouts."""

    timeout_seconds = API_CONFIG["moex_iss"]["timeout_seconds"]
    exclusive_end_date = end_date + timedelta(days=1)

    try:
        stock = yf.Ticker(ticker)
        return stock.history(
            start=start_date,
            end=exclusive_end_date,
            auto_adjust=False,
            timeout=timeout_seconds,
            raise_errors=True,
        )
    except curl_requests.exceptions.Timeout as exc:
        raise UpstreamTimeoutError(f"Yahoo Finance timed out for {ticker}", exc) from exc
    except YFRateLimitError as exc:
        raise UpstreamConnectionError(f"Yahoo Finance rate-limited {ticker}", exc) from exc
    except (
        curl_requests.exceptions.ConnectionError,
        curl_requests.exceptions.RequestException,
    ) as exc:
        raise UpstreamConnectionError(f"Yahoo Finance connection failed for {ticker}", exc) from exc
    except (YFPricesMissingError, YFTzMissingError) as exc:
        raise DataSourceError(
            f"Yahoo Finance returned no data for {ticker}",
            exc,
            error_code="no_data",
        ) from exc
    except Exception as exc:
        raise DataSourceError(
            f"Yahoo Finance returned an unexpected response for {ticker}",
            exc,
            error_code="schema_error",
        ) from exc


@st.cache_data(
    ttl=CACHE_CONFIG["ttl_seconds"],
    max_entries=CACHE_CONFIG.get("max_entries", 50),
)
def _load_cached_usd_rates(start_date: date, end_date: date) -> FxRateWindow:
    """Load and cache only successful FX windows."""

    try_frame = _fetch_yfinance_history("TRY=X", start_date, end_date)
    rub_frame = _fetch_yfinance_history("RUB=X", start_date, end_date)
    try_series = _sanitize_close_series(try_frame).to_frame(name="USD_TRY")
    rub_series = _sanitize_close_series(rub_frame).to_frame(name="USD_RUB")
    if try_series.empty or rub_series.empty:
        raise DataSourceError(
            "Yahoo Finance FX window is incomplete",
            error_code="conversion_incomplete",
        )

    return FxRateWindow(usd_try=try_series, usd_rub=rub_series)


def fetch_usd_rates(start_date: date, end_date: date) -> OperationResult[FxRateWindow]:
    """Fetch USD/TRY and USD/RUB exchange rates from Yahoo Finance."""

    requested_range = _validate_requested_window(start_date, end_date)
    if requested_range is None:
        return error_result("unsupported_window", None)

    try:
        payload = _load_cached_usd_rates(start_date, end_date)
        return success_result(payload, requested_range, requested_range)
    except UpstreamTimeoutError:
        return error_result("timeout", requested_range)
    except UpstreamConnectionError:
        return error_result("connection", requested_range)
    except DataSourceError as exc:
        logger.warning("FX rate fetch failed: %s", exc)
        return error_result(exc.error_code, requested_range)


def convert_to_usd(
    prices: pd.Series,
    currency_code: str,
    usd_rates: FxRateWindow,
) -> pd.Series:
    """Convert a local-currency series to USD using exact shared FX dates only."""

    target_rate_df = None
    if currency_code == "TRY":
        target_rate_df = usd_rates.usd_try
    elif currency_code == "RUB":
        target_rate_df = usd_rates.usd_rub

    if target_rate_df is None or prices.empty:
        return prices.iloc[0:0]

    clean_prices = _sanitize_numeric_series(prices)
    if clean_prices.empty or target_rate_df.empty:
        return clean_prices.iloc[0:0]

    rate_col = target_rate_df.columns[0]
    clean_rates = _sanitize_numeric_series(target_rate_df[rate_col]).rename(rate_col)
    aligned = clean_prices.rename("price").to_frame().join(clean_rates.to_frame(), how="inner")
    if aligned.empty:
        return clean_prices.iloc[0:0]

    prices_arr = aligned["price"].astype(str).values
    rates_arr = aligned[rate_col].astype(str).values

    converted: list[Decimal] = []
    converted_index: list[pd.Timestamp] = []

    for idx, p_str, r_str in zip(aligned.index, prices_arr, rates_arr, strict=True):
        try:
            price_value = Decimal(p_str)
            rate_value = Decimal(r_str)
            if rate_value > 0 and price_value > 0:
                converted.append(price_value / rate_value)
                converted_index.append(pd.Timestamp(idx))
        except (InvalidOperation, TypeError, ValueError):
            continue

    return pd.Series(converted, index=pd.DatetimeIndex(converted_index))


def _build_monthly_cpi_index(monthly_change_pct: dict[str, object]) -> pd.Series:
    """Build a cumulative monthly CPI index from monthly percentage changes."""

    cumulative_index = Decimal("100")
    values: list[float] = []
    index: list[pd.Timestamp] = []

    for month_key in sorted(monthly_change_pct):
        try:
            monthly_change = Decimal(str(monthly_change_pct[month_key]))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise DataSourceError(
                f"Invalid CPI snapshot value for {month_key}",
                exc,
                error_code="inflation_incomplete",
            ) from exc

        cumulative_index *= Decimal("1") + (monthly_change / Decimal("100"))
        index.append(pd.Timestamp(f"{month_key}-01"))
        values.append(float(cumulative_index))

    return pd.Series(values, index=pd.DatetimeIndex(index), name="CPI")


def _get_country_cpi_series(country_code: str) -> pd.Series:
    """Return the configured monthly CPI index series for a country code."""

    monthly_change_pct = INFLATION_CONFIG.get("monthly_change_pct", {}).get(country_code)
    if not isinstance(monthly_change_pct, dict) or not monthly_change_pct:
        raise DataSourceError(
            f"CPI snapshot is unavailable for {country_code}",
            error_code="inflation_incomplete",
        )

    return _build_monthly_cpi_index(monthly_change_pct)


def _month_start(value: date | pd.Timestamp) -> pd.Timestamp:
    """Return the normalized first day of the month."""

    return pd.Timestamp(value).to_period("M").to_timestamp()


def _month_end(value: pd.Timestamp) -> date:
    """Return the last calendar day of the month."""

    return (value + pd.offsets.MonthEnd(0)).date()


def _has_complete_monthly_coverage(
    cpi_series: pd.Series,
    start_month: pd.Timestamp,
    end_month: pd.Timestamp,
) -> bool:
    """Return True when every month in the requested span exists in the CPI series."""

    expected_months = pd.period_range(start_month, end_month, freq="M")
    available_months = set(cpi_series.index.to_period("M"))
    return all(month in available_months for month in expected_months)


@st.cache_data(
    ttl=CACHE_CONFIG["ttl_seconds"],
    max_entries=CACHE_CONFIG.get("max_entries", 50),
)
def _load_cached_inflation_window(start_date: date, end_date: date) -> InflationWindow:
    """Load a shared monthly CPI window for real-return calculations."""

    tr_cpi = _get_country_cpi_series("TR")
    ru_cpi = _get_country_cpi_series("RU")
    start_month = _month_start(start_date)
    requested_end_month = _month_start(end_date)

    tr_supported_months = tr_cpi[tr_cpi.index <= requested_end_month].index
    ru_supported_months = ru_cpi[ru_cpi.index <= requested_end_month].index
    if tr_supported_months.empty or ru_supported_months.empty:
        raise DataSourceError(
            "CPI snapshot does not overlap the requested period",
            error_code="inflation_incomplete",
        )

    shared_base_month = min(tr_supported_months.max(), ru_supported_months.max())
    if shared_base_month < start_month:
        raise DataSourceError(
            "CPI snapshot starts after the requested comparison window",
            error_code="inflation_incomplete",
        )

    if not _has_complete_monthly_coverage(tr_cpi, start_month, shared_base_month):
        raise DataSourceError(
            "TR CPI snapshot has a gap inside the requested window",
            error_code="inflation_incomplete",
        )

    if not _has_complete_monthly_coverage(ru_cpi, start_month, shared_base_month):
        raise DataSourceError(
            "RU CPI snapshot has a gap inside the requested window",
            error_code="inflation_incomplete",
        )

    return InflationWindow(
        tr_cpi=tr_cpi[(tr_cpi.index >= start_month) & (tr_cpi.index <= shared_base_month)],
        ru_cpi=ru_cpi[(ru_cpi.index >= start_month) & (ru_cpi.index <= shared_base_month)],
        shared_base_month=shared_base_month,
    )


def fetch_inflation_window(
    start_date: date,
    end_date: date,
) -> OperationResult[InflationWindow]:
    """Fetch the shared CPI window used to calculate real returns."""

    requested_range = _validate_requested_window(start_date, end_date)
    if requested_range is None:
        return error_result("unsupported_window", None)

    try:
        payload = _load_cached_inflation_window(start_date, end_date)
    except DataSourceError as exc:
        logger.warning("CPI snapshot fetch failed: %s", exc)
        return error_result(exc.error_code, requested_range)

    effective_end = min(end_date, _month_end(payload.shared_base_month))
    effective_range = build_date_range(start_date, effective_end)
    return success_result(
        payload,
        requested_range,
        effective_range,
        is_complete=effective_end >= end_date,
    )


def convert_to_real(
    prices: pd.Series,
    country_code: str,
    inflation_window: InflationWindow,
) -> pd.Series:
    """Convert a nominal price series into end-of-window purchasing-power terms."""

    if prices.empty:
        return prices.iloc[0:0]

    clean_prices = _sanitize_numeric_series(prices)
    if clean_prices.empty:
        return clean_prices

    cpi_series = None
    if country_code == "TR":
        cpi_series = inflation_window.tr_cpi
    elif country_code == "RU":
        cpi_series = inflation_window.ru_cpi

    if cpi_series is None or cpi_series.empty:
        return clean_prices.iloc[0:0]

    base_month = inflation_window.shared_base_month.to_period("M")
    cpi_by_month = {
        month.to_period("M"): Decimal(str(value))
        for month, value in cpi_series.items()
    }
    base_cpi = cpi_by_month.get(base_month)
    if base_cpi is None or base_cpi <= 0:
        return clean_prices.iloc[0:0]

    supported_prices = clean_prices[clean_prices.index.to_period("M") <= base_month]
    if supported_prices.empty:
        return clean_prices.iloc[0:0]

    converted_values: list[float] = []
    converted_index: list[pd.Timestamp] = []
    for index_value, price in supported_prices.items():
        month = pd.Timestamp(index_value).to_period("M")
        cpi_value = cpi_by_month.get(month)
        if cpi_value is None or cpi_value <= 0:
            return clean_prices.iloc[0:0]

        converted_values.append(float(Decimal(str(price)) * base_cpi / cpi_value))
        converted_index.append(pd.Timestamp(index_value))

    return pd.Series(converted_values, index=pd.DatetimeIndex(converted_index))


def _fetch_moex_iss_candles(
    ticker: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Fetch daily candles from the official MOEX ISS REST API."""

    base_url = API_CONFIG["moex_iss"]["base_url"]
    timeout = API_CONFIG["moex_iss"]["timeout_seconds"]
    max_retries = API_CONFIG["moex_iss"]["max_retries"]
    retry_delay = API_CONFIG["moex_iss"]["retry_delay_seconds"]
    session = _get_moex_session()
    from_str = start_date.strftime("%Y-%m-%d")
    till_str = end_date.strftime("%Y-%m-%d")

    all_rows: list[tuple[str, object]] = []
    offset = 0
    pages_fetched = 0

    while pages_fetched < _MOEX_ISS_MAX_PAGES:
        url = _MOEX_ISS_CANDLES_URL.format(
            base=base_url,
            ticker=ticker,
            from_date=from_str,
            till_date=till_str,
            offset=offset,
        )

        response = None
        for attempt in range(max_retries):
            try:
                response = session.get(url, timeout=timeout)
            except requests.exceptions.Timeout as exc:
                if attempt == max_retries - 1:
                    raise UpstreamTimeoutError(
                        f"MOEX ISS timed out after {max_retries} attempts",
                        exc,
                    ) from exc
                time.sleep(retry_delay)
                continue
            except requests.exceptions.ConnectionError as exc:
                if attempt == max_retries - 1:
                    raise UpstreamConnectionError("MOEX ISS connection failed", exc) from exc
                time.sleep(retry_delay)
                continue
            except requests.exceptions.RequestException as exc:
                if attempt == max_retries - 1:
                    raise UpstreamConnectionError("MOEX ISS request failed", exc) from exc
                time.sleep(retry_delay)
                continue

            if response.status_code in {400, 404}:
                raise DataSourceError(
                    "MOEX ISS returned no data for the requested security",
                    error_code="no_data",
                )

            if response.status_code >= 500:
                raise UpstreamConnectionError("MOEX ISS returned a server error")

            if response.status_code >= 300:
                raise DataSourceError(
                    "MOEX ISS returned an unsupported response",
                    error_code="schema_error",
                )
            break

        if response is None:
            raise DataSourceError("MOEX ISS response was empty", error_code="schema_error")

        try:
            payload = response.json()
        except Exception as exc:
            raise DataSourceError(
                "Failed to parse MOEX ISS JSON",
                exc,
                error_code="schema_error",
            ) from exc

        candles_block = payload.get("candles", {})
        columns = candles_block.get("columns", [])
        data = candles_block.get("data", [])
        if not columns or not data:
            break

        try:
            close_idx = columns.index("close")
            begin_idx = columns.index("begin")
        except ValueError as exc:
            raise DataSourceError(
                "MOEX ISS schema changed unexpectedly",
                exc,
                error_code="schema_error",
            ) from exc

        all_rows.extend((row[begin_idx], row[close_idx]) for row in data)
        pages_fetched += 1
        if len(data) < _MOEX_ISS_PAGE_SIZE:
            break

        offset += len(data)

    if pages_fetched >= _MOEX_ISS_MAX_PAGES:
        logger.warning(
            "MOEX ISS pagination limit reached for %s (%d pages). "
            "Returning partial data.",
            ticker,
            _MOEX_ISS_MAX_PAGES,
        )

    if not all_rows:
        return pd.DataFrame(columns=["Close"])

    data_frame = pd.DataFrame(all_rows, columns=["Date", "Close"])
    data_frame["Date"] = pd.to_datetime(data_frame["Date"], errors="coerce")
    data_frame["Close"] = pd.to_numeric(data_frame["Close"], errors="coerce")
    data_frame = data_frame.dropna(subset=["Date", "Close"])
    data_frame = data_frame.set_index("Date").sort_index()
    data_frame.index = data_frame.index.normalize()
    return data_frame


def fetch_moex_iss_data(
    ticker: str,
    start_date: date,
    end_date: date,
) -> OperationResult[pd.Series]:
    """Fetch MOEX stock data using the standard operation result contract."""

    requested_range = _validate_requested_window(start_date, end_date)
    if requested_range is None:
        return error_result("unsupported_window", None)

    try:
        data_frame = _fetch_moex_iss_candles(ticker, start_date, end_date)
        close_series = _sanitize_close_series(data_frame)
        if close_series.empty:
            return error_result("no_data", requested_range)

        min_points = DATA_CONFIG["min_data_points"]
        if len(close_series) < min_points:
            return error_result("insufficient_data", requested_range)

        return _build_price_success(close_series, requested_range)
    except UpstreamTimeoutError:
        return error_result("timeout", requested_range)
    except UpstreamConnectionError:
        return error_result("connection", requested_range)
    except DataSourceError as exc:
        logger.warning("MOEX ISS fetch failed for %s: %s", ticker, exc)
        return error_result(exc.error_code, requested_range)


@st.cache_data(
    ttl=CACHE_CONFIG["ttl_seconds"],
    max_entries=CACHE_CONFIG.get("max_entries", 50),
)
def _load_cached_stock_series(
    ticker: str,
    start_date: date,
    end_date: date,
    is_russian: bool = False,
) -> pd.Series:
    """Load and cache only successful stock series."""

    if is_russian:
        data_frame = _fetch_moex_iss_candles(ticker, start_date, end_date)
    else:
        data_frame = _fetch_yfinance_history(ticker, start_date, end_date)

    close_series = _sanitize_close_series(data_frame)
    if close_series.empty:
        raise DataSourceError(
            f"No data returned for {ticker}",
            error_code="no_data",
        )

    min_points = DATA_CONFIG["min_data_points"]
    if len(close_series) < min_points:
        raise DataSourceError(
            f"Insufficient data returned for {ticker}",
            error_code="insufficient_data",
        )

    return close_series


def fetch_stock_data(
    ticker: str,
    start_date: date,
    end_date: date,
    is_russian: bool = False,
) -> OperationResult[pd.Series]:
    """Fetch stock data with robust, typed error handling."""

    requested_range = _validate_requested_window(start_date, end_date)
    if requested_range is None:
        return error_result("unsupported_window", None)

    try:
        close_series = _load_cached_stock_series(ticker, start_date, end_date, is_russian)
        return _build_price_success(close_series, requested_range)
    except UpstreamTimeoutError:
        return error_result("timeout", requested_range)
    except UpstreamConnectionError:
        return error_result("connection", requested_range)
    except DataSourceError as exc:
        provider_name = "MOEX ISS" if is_russian else "Yahoo Finance"
        logger.warning("%s fetch failed for %s: %s", provider_name, ticker, exc)
        return error_result(exc.error_code, requested_range)


async def fetch_stock_data_async(
    ticker: str,
    start_date: date,
    end_date: date,
    is_russian: bool = False,
) -> OperationResult[pd.Series]:
    """Async wrapper around the cached stock fetcher."""

    return await asyncio.to_thread(fetch_stock_data, ticker, start_date, end_date, is_russian)


async def fetch_usd_rates_async(
    start_date: date,
    end_date: date,
) -> OperationResult[FxRateWindow]:
    """Async wrapper for FX rates."""

    return await asyncio.to_thread(fetch_usd_rates, start_date, end_date)


async def fetch_inflation_window_async(
    start_date: date,
    end_date: date,
) -> OperationResult[InflationWindow]:
    """Async wrapper for curated CPI coverage."""

    return await asyncio.to_thread(fetch_inflation_window, start_date, end_date)


async def fetch_ytd_start_price(
    ticker: str,
    selected_end_date: date,
    is_russian: bool = False,
) -> OperationResult[Decimal]:
    """Fetch the first trading-day close for the selected end-year."""

    start_year = date(selected_end_date.year, 1, 1)
    end_january = date(selected_end_date.year, 1, 31)
    requested_range = _build_requested_range(start_year, end_january)
    result = await fetch_stock_data_async(ticker, start_year, end_january, is_russian)
    if not result.is_success or result.payload is None or result.payload.empty:
        return error_result(result.error_code or "no_data", requested_range)

    first_close = result.payload.iloc[0]
    try:
        baseline = Decimal(str(first_close))
    except (InvalidOperation, TypeError, ValueError):
        return error_result("schema_error", requested_range)

    effective_range = _build_date_range_for_single_day(result.payload.index[0])
    return success_result(
        baseline,
        requested_range,
        effective_range,
        is_complete=True,
    )


async def fetch_market_cap_async(
    ticker: str,
    is_russian: bool = False,
) -> OperationResult[float]:
    """Fetch market-cap data from the curated configuration snapshot."""

    _ = is_russian
    cap = MARKET_CAPS.get(ticker)
    if cap is None:
        return error_result("no_data", None)

    try:
        cap_value = float(cap)
    except (TypeError, ValueError):
        logger.warning("Market-cap snapshot is invalid for %s: %r", ticker, cap)
        return error_result("no_data", None)

    return success_result(cap_value, None, None)


def _build_date_range_for_single_day(value: pd.Timestamp) -> DateRange:
    """Build a single-day effective range."""

    single_day = pd.Timestamp(value).date()
    return build_date_range(single_day, single_day)

fetch_stock_data.clear = _load_cached_stock_series.clear  # type: ignore[attr-defined]
fetch_usd_rates.clear = _load_cached_usd_rates.clear  # type: ignore[attr-defined]
fetch_inflation_window.clear = _load_cached_inflation_window.clear  # type: ignore[attr-defined]
