"""
Deterministic robustness tests for dashboard orchestration.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pandas as pd

from src.dashboard import calculate_ytd_change, prepare_comparison_series
from src.models import FxRateWindow, build_date_range, error_result, success_result


def _build_price_result(
    values: list[float],
    index: pd.DatetimeIndex,
) -> object:
    requested_range = build_date_range(date(2024, 1, 1), date(2024, 1, 31))
    effective_range = build_date_range(index.min().date(), index.max().date())
    return success_result(pd.Series(values, index=index), requested_range, effective_range)


class TestDashboardRobustness:
    """Deterministic tests for fail-closed dashboard logic."""

    def test_calculate_ytd_change_requires_both_inputs(self) -> None:
        price_result = _build_price_result([100.0, 110.0, 120.0, 130.0, 140.0], pd.date_range("2024-01-10", periods=5))
        baseline_error = error_result("no_data", build_date_range(date(2024, 1, 1), date(2024, 1, 31)))

        result = calculate_ytd_change(price_result, baseline_error)

        assert result.status == "error"
        assert result.error_code == "insufficient_data"

    def test_calculate_ytd_change_rejects_incomplete_baseline(self) -> None:
        price_result = _build_price_result([200.0, 240.0, 260.0, 280.0, 300.0], pd.date_range("2024-01-10", periods=5))
        baseline_result = success_result(
            Decimal("150.0"),
            build_date_range(date(2024, 1, 1), date(2024, 1, 31)),
            build_date_range(date(2024, 1, 15), date(2024, 1, 15)),
            is_complete=False,
        )

        result = calculate_ytd_change(price_result, baseline_result)

        assert result.status == "error"
        assert result.error_code == "insufficient_data"

    def test_prepare_comparison_series_requires_shared_usd_overlap(self) -> None:
        tr_result = _build_price_result([100, 101, 102, 103, 104], pd.date_range("2024-01-01", periods=5))
        ru_result = _build_price_result([200, 201, 202, 203, 204], pd.date_range("2024-01-01", periods=5))
        fx_payload = FxRateWindow(
            usd_try=pd.DataFrame({"USD_TRY": [30.0]}, index=pd.to_datetime(["2024-01-05"])),
            usd_rub=pd.DataFrame({"USD_RUB": [90.0]}, index=pd.to_datetime(["2024-01-05"])),
        )
        fx_result = success_result(
            fx_payload,
            build_date_range(date(2024, 1, 1), date(2024, 1, 31)),
            build_date_range(date(2024, 1, 1), date(2024, 1, 31)),
        )

        result = prepare_comparison_series(tr_result, ru_result, fx_result, True, min_points=5)

        assert result.status == "error"
        assert result.error_code == "conversion_incomplete"

    def test_prepare_comparison_series_local_mode_aligns_to_shared_window(self) -> None:
        tr_result = _build_price_result([100, 101, 102, 103, 104], pd.date_range("2024-01-01", periods=5))
        ru_result = _build_price_result([200, 201, 202, 203], pd.date_range("2024-01-02", periods=4))

        result = prepare_comparison_series(
            tr_result,
            ru_result,
            error_result("conversion_incomplete", None),
            False,
            min_points=4,
        )

        assert result.is_success
        assert result.payload is not None
        assert not result.is_complete
        assert result.payload.tr_series.index.min().date() == date(2024, 1, 2)
        assert result.payload.ru_series.index.min().date() == date(2024, 1, 2)
        assert len(result.payload.tr_series) == 4
        assert len(result.payload.ru_series) == 4

    def test_prepare_comparison_series_allows_partial_but_safe_overlap(self) -> None:
        tr_result = _build_price_result([100, 101, 102, 103, 104], pd.date_range("2024-01-01", periods=5))
        ru_result = _build_price_result([200, 201, 202, 203, 204], pd.date_range("2024-01-01", periods=5))
        fx_index = pd.date_range("2024-01-02", periods=4)
        fx_payload = FxRateWindow(
            usd_try=pd.DataFrame({"USD_TRY": [30.0, 30.1, 30.2, 30.3]}, index=fx_index),
            usd_rub=pd.DataFrame({"USD_RUB": [90.0, 90.1, 90.2, 90.3]}, index=fx_index),
        )
        fx_result = success_result(
            fx_payload,
            build_date_range(date(2024, 1, 1), date(2024, 1, 31)),
            build_date_range(date(2024, 1, 1), date(2024, 1, 31)),
        )

        result = prepare_comparison_series(tr_result, ru_result, fx_result, True, min_points=4)

        assert result.is_success
        assert result.payload is not None
        assert not result.is_complete
        assert len(result.payload.tr_series) == 4
        assert result.effective_range == build_date_range(date(2024, 1, 2), date(2024, 1, 5))

    def test_market_cap_missing_stays_unavailable(self) -> None:
        from src.data import fetch_market_cap_async

        result = __import__("asyncio").run(fetch_market_cap_async("UNKNOWN", is_russian=True))

        assert result.status == "error"
        assert result.error_code == "no_data"

    def test_market_cap_invalid_snapshot_stays_unavailable(self) -> None:
        from src.data import fetch_market_cap_async

        with patch.dict("src.data.MARKET_CAPS", {"BROKEN": "not-a-number"}, clear=False):
            result = __import__("asyncio").run(fetch_market_cap_async("BROKEN", is_russian=True))

        assert result.status == "error"
        assert result.error_code == "no_data"

    def test_ytd_result_preserves_selected_year_baseline(self) -> None:
        price_result = _build_price_result([200.0, 240.0, 260.0, 280.0, 300.0], pd.date_range("2024-01-10", periods=5))
        baseline_result = success_result(
            Decimal("150.0"),
            build_date_range(date(2024, 1, 1), date(2024, 1, 31)),
            build_date_range(date(2024, 1, 2), date(2024, 1, 2)),
        )

        result = calculate_ytd_change(price_result, baseline_result)

        assert result.is_success
        assert result.payload == 100.0
