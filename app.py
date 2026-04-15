"""
The Eurasian Bridge: BIST vs. MOEX Analyzer.
"""

from __future__ import annotations

import logging
import os
from datetime import date, datetime, timedelta
from typing import cast
from zoneinfo import ZoneInfo

import streamlit as st

from src.analysis import (
    calculate_cagr,
    calculate_change_pct,
    calculate_correlation,
    calculate_maximum_drawdown,
    calculate_sharpe_ratio,
    calculate_volatility,
    normalize_to_base_100,
)
from src.config import (
    APP_CONFIG,
    COLORS,
    DATA_CONFIG,
    LANGUAGE_OPTIONS,
    MARKET_CAP_METADATA,
    SECTORS,
    get_macro_events_in_range,
    get_sector_options,
    get_text,
)
from src.dashboard import (
    calculate_ytd_change,
    calculate_ytd_change_real,
    calculate_ytd_change_usd,
    load_dashboard_data,
    prepare_comparison_series,
)
from src.models import AnalysisMode, DashboardPayload, OperationResult, SeriesPair, error_result
from src.ui import (
    create_normalized_chart,
    format_metric_value,
    get_custom_css,
    render_correlation_card,
    render_market_cap_card,
    render_methodology_card,
    render_metric_card,
    render_risk_summary_card,
    render_ytd_card,
    show_error,
)

# Configure structured logging before any execution
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

if "SENTRY_DSN" in os.environ:
    import sentry_sdk

    sentry_sdk.init(
        dsn=os.environ["SENTRY_DSN"],
        traces_sample_rate=1.0,
    )
    logging.info("Sentry APM initialized.")


def build_market_cap_source_note(lang: str) -> str:
    """Build a localized note for the market-cap snapshot source."""

    as_of = MARKET_CAP_METADATA.get("as_of", "N/A")
    source_text = get_text("market_cap_source_note", lang, as_of=as_of)
    disclaimer = get_text("market_cap_snapshot_disclaimer", lang)
    return f"{source_text} {disclaimer}"


def build_methodology_points(lang: str) -> list[str]:
    """Build the localized methodology bullets shown below the analysis."""

    return [
        get_text("methodology_point_1", lang),
        get_text("methodology_point_2", lang),
        get_text("methodology_point_3", lang),
        get_text("methodology_point_4", lang),
        get_text("methodology_point_5", lang),
        get_text("methodology_point_6", lang),
    ]


def build_risk_summary_items(lang: str) -> list[tuple[str, str]]:
    """Build the localized summary bullets for the risk-metrics footer card."""

    return [
        (get_text("volatility", lang), get_text("volatility_summary", lang)),
        (get_text("sharpe_ratio", lang), get_text("sharpe_ratio_summary", lang)),
        (get_text("max_drawdown", lang), get_text("max_drawdown_summary", lang)),
        (get_text("cagr", lang), get_text("cagr_summary", lang)),
    ]


def render_banner(message: str, banner_class: str) -> None:
    """Render a shared banner block."""

    st.markdown(f'<div class="{banner_class}">{message}</div>', unsafe_allow_html=True)


def render_source_status(
    result: OperationResult[object],
    ticker: str,
    lang: str,
    success_key: str,
) -> None:
    """Render source-level status and delayed-data warnings."""

    if not result.is_success:
        show_error(result, ticker, lang)
        return

    render_banner(f"{get_text(success_key, lang)} ({ticker})", "success-banner")
    if (
        result.effective_range is None
        or result.requested_range is None
        or result.effective_range.end >= result.requested_range.end
    ):
        return

    message = get_text(
        "date_adjusted",
        lang,
        actual_date=result.effective_range.end.strftime("%d/%m/%Y"),
        requested_date=result.requested_range.end.strftime("%d/%m/%Y"),
    )
    render_banner(message, "warning-banner")


def render_general_overview(
    payload: DashboardPayload,
    sector_data: dict[str, str],
    end_date: date,
    lang: str,
    *,
    analysis_mode: AnalysisMode = "local",
) -> None:
    """Render YTD and market-cap overview cards."""

    if analysis_mode == "usd" and payload.usd_rates.is_success and payload.usd_rates.payload is not None:
        tr_ytd_result = calculate_ytd_change_usd(
            payload.tr_result, payload.tr_ytd_start, "TRY", payload.usd_rates.payload,
        )
        ru_ytd_result = calculate_ytd_change_usd(
            payload.ru_result, payload.ru_ytd_start, "RUB", payload.usd_rates.payload,
        )
    elif (
        analysis_mode == "real"
        and payload.inflation_window.is_success
        and payload.inflation_window.payload is not None
    ):
        tr_ytd_result = calculate_ytd_change_real(
            payload.tr_result, payload.tr_ytd_start, "TR", payload.inflation_window.payload,
        )
        ru_ytd_result = calculate_ytd_change_real(
            payload.ru_result, payload.ru_ytd_start, "RU", payload.inflation_window.payload,
        )
    elif analysis_mode == "real":
        tr_ytd_result = error_result("inflation_incomplete", payload.tr_result.requested_range)
        ru_ytd_result = error_result("inflation_incomplete", payload.ru_result.requested_range)
    else:
        tr_ytd_result = calculate_ytd_change(payload.tr_result, payload.tr_ytd_start)
        ru_ytd_result = calculate_ytd_change(payload.ru_result, payload.ru_ytd_start)

    st.markdown(
        f'<div class="section-header">🌍 {get_text("general_overview", lang)}</div>',
        unsafe_allow_html=True,
    )

    col_ytd, col_cap = st.columns(2)
    with col_ytd:
        render_ytd_card(
            tr_ytd_result.payload if tr_ytd_result.is_success else None,
            ru_ytd_result.payload if ru_ytd_result.is_success else None,
            sector_data["TR"],
            sector_data["RU"],
            year=end_date.year,
            lang=lang,
        )

    with col_cap:
        render_market_cap_card(
            payload.tr_cap.payload if payload.tr_cap.is_success else None,
            payload.ru_cap.payload if payload.ru_cap.is_success else None,
            lang,
            source_note=build_market_cap_source_note(lang),
        )


def render_current_metrics(series_pair: SeriesPair, sector_data: dict[str, str], lang: str) -> None:
    """Render the current-price cards."""

    st.markdown(f'<div class="section-header">{get_text("current_metrics", lang)}</div>', unsafe_allow_html=True)

    tr_series = series_pair.tr_series
    ru_series = series_pair.ru_series
    tr_change = calculate_change_pct(tr_series)
    ru_change = calculate_change_pct(ru_series)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card(
            f"🇹🇷 {sector_data['TR']}",
            format_metric_value(
                tr_series.iloc[-1],
                lang,
                decimals=2,
                prefix=series_pair.tr_currency,
            ),
            tr_change,
        )

    with col2:
        render_metric_card(
            get_text("tr_period_change", lang),
            format_metric_value(tr_change, lang, decimals=2, suffix="%", signed=True),
            None,
            help_text=get_text(
                "start_price_label",
                lang,
                currency=series_pair.tr_currency,
                price=f"{tr_series.iloc[0]:,.2f}",
                date=tr_series.index[0].strftime("%d/%m/%Y"),
            ),
        )

    with col3:
        render_metric_card(
            f"🇷🇺 {sector_data['RU']}",
            format_metric_value(
                ru_series.iloc[-1],
                lang,
                decimals=2,
                prefix=series_pair.ru_currency,
            ),
            ru_change,
        )

    with col4:
        render_metric_card(
            get_text("ru_period_change", lang),
            format_metric_value(ru_change, lang, decimals=2, suffix="%", signed=True),
            None,
            help_text=get_text(
                "start_price_label",
                lang,
                currency=series_pair.ru_currency,
                price=f"{ru_series.iloc[0]:,.2f}",
                date=ru_series.index[0].strftime("%d/%m/%Y"),
            ),
        )


def render_risk_metrics(series_pair: SeriesPair, lang: str) -> None:
    """Render the risk metrics cards."""

    st.markdown(f'<div class="section-header">{get_text("risk_metrics", lang)}</div>', unsafe_allow_html=True)

    tr_series = series_pair.tr_series
    ru_series = series_pair.ru_series
    tr_volatility = calculate_volatility(tr_series)
    tr_sharpe = calculate_sharpe_ratio(tr_series)
    ru_volatility = calculate_volatility(ru_series)
    ru_sharpe = calculate_sharpe_ratio(ru_series)
    tr_drawdown = calculate_maximum_drawdown(tr_series)
    tr_cagr = calculate_cagr(tr_series)
    ru_drawdown = calculate_maximum_drawdown(ru_series)
    ru_cagr = calculate_cagr(ru_series)

    top_row = st.columns(4)
    top_row[0].markdown(render_metric_html(get_text("volatility", lang), tr_volatility, lang, "%"), unsafe_allow_html=True)
    top_row[1].markdown(render_metric_html(get_text("sharpe_ratio", lang), tr_sharpe, lang, ""), unsafe_allow_html=True)
    top_row[2].markdown(render_metric_html(get_text("volatility", lang), ru_volatility, lang, "%"), unsafe_allow_html=True)
    top_row[3].markdown(render_metric_html(get_text("sharpe_ratio", lang), ru_sharpe, lang, ""), unsafe_allow_html=True)

    bottom_row = st.columns(4)
    bottom_row[0].markdown(render_metric_html(get_text("max_drawdown", lang), tr_drawdown, lang, "%"), unsafe_allow_html=True)
    bottom_row[1].markdown(render_metric_html(get_text("cagr", lang), tr_cagr, lang, "%"), unsafe_allow_html=True)
    bottom_row[2].markdown(render_metric_html(get_text("max_drawdown", lang), ru_drawdown, lang, "%"), unsafe_allow_html=True)
    bottom_row[3].markdown(render_metric_html(get_text("cagr", lang), ru_cagr, lang, "%"), unsafe_allow_html=True)


def render_metric_html(label: str, value: float | None, lang: str, suffix: str) -> str:
    """Render a metric card via HTML when a compact grid is enough."""

    display_value = format_metric_value(value, lang, decimals=2 if suffix == "" else 1, suffix=suffix)
    return (
        f'<div class="metric-card">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{display_value}</div>'
        f"</div>"
    )


def render_chart(
    series_pair: SeriesPair,
    sector_data: dict[str, str],
    start_date: date,
    end_date: date,
    lang: str,
) -> None:
    """Render the normalized comparison chart when the pair is valid."""

    st.markdown(
        f'<div class="section-header">{get_text("normalized_performance", lang)}</div>',
        unsafe_allow_html=True,
    )

    tr_normalized = normalize_to_base_100(series_pair.tr_series)
    ru_normalized = normalize_to_base_100(series_pair.ru_series)
    if len(tr_normalized) < 2 or len(ru_normalized) < 2:
        render_banner(get_text("chart_unavailable", lang), "warning-banner")
        return

    macro_events = get_macro_events_in_range(start_date, end_date, lang)
    figure = create_normalized_chart(
        tr_normalized,
        ru_normalized,
        tr_ticker=sector_data["TR"],
        ru_ticker=sector_data["RU"],
        lang=lang,
        currency_label=series_pair.currency_label,
        macro_events=macro_events,
    )
    st.plotly_chart(figure, width="stretch")


def render_correlation(series_pair: SeriesPair, lang: str) -> None:
    """Render the correlation card when enough aligned data exists."""

    st.markdown(
        f'<div class="section-header">{get_text("correlation_analysis", lang)}</div>',
        unsafe_allow_html=True,
    )

    tr_returns = series_pair.tr_series.pct_change().dropna()
    ru_returns = series_pair.ru_series.pct_change().dropna()
    correlation = calculate_correlation(tr_returns, ru_returns)
    if correlation is None:
        render_banner(get_text("correlation_unavailable", lang), "warning-banner")
        return

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        render_correlation_card(correlation, lang)

    st.markdown(
        f"""
        <div style="background-color: {COLORS['card_bg']}; padding: 1.5rem; border-radius: 8px; margin-top: 1rem;">
            <h4 style="color: {COLORS['primary']}; font-family: Georgia, serif; margin-bottom: 1rem;">
                {get_text("interpretation_guide", lang)}
            </h4>
            <p style="color: {COLORS['text_dark']}; font-family: Arial, sans-serif; font-size: 0.9rem; line-height: 1.6;">
                {get_text("interpretation_text", lang)}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(
    page_title=f"{APP_CONFIG['title']} v2.0",
    page_icon=APP_CONFIG["icon"],
    layout=APP_CONFIG["layout"],
    initial_sidebar_state=APP_CONFIG["sidebar_state"],
)
st.markdown(get_custom_css(), unsafe_allow_html=True)

with st.sidebar:
    st.markdown(
        """
        <div style="text-align: center; padding: 0.5rem 0;">
            <span style="font-size: 2.5rem;">🌉</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    selected_language = st.selectbox(
        "🌐 Language / Dil / Язык",
        options=list(LANGUAGE_OPTIONS.keys()),
        index=0,
    )
    lang = LANGUAGE_OPTIONS[selected_language]

    st.markdown(
        f"""
        <div style="text-align: center; padding: 0.5rem 0;">
            <h2 style="color: {COLORS['primary']}; font-family: Georgia, serif; margin: 0.5rem 0;">
                {get_text("sector_analysis", lang)}
            </h2>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    sector_options = get_sector_options(lang)
    selected_sector_display = st.selectbox(
        get_text("select_sector", lang),
        options=list(sector_options.keys()),
        index=0,
        help=get_text("sector_help", lang),
    )
    selected_sector_id = sector_options[selected_sector_display]

    st.markdown("---")
    st.markdown(
        f"<p style='color: {COLORS['text_dark']}; font-weight: 600;'>{get_text('analysis_period', lang)}</p>",
        unsafe_allow_html=True,
    )
    moex_delay = DATA_CONFIG["moex_delay_days"]
    default_lookback = DATA_CONFIG["default_lookback_days"]
    date_columns = st.columns(2)
    with date_columns[0]:
        start_date = st.date_input(
            get_text("start", lang),
            value=datetime.now(tz=ZoneInfo("Europe/Istanbul")) - timedelta(days=default_lookback),
            max_value=datetime.now(tz=ZoneInfo("Europe/Istanbul")),
            format="DD/MM/YYYY",
        )
    with date_columns[1]:
        end_date = st.date_input(
            get_text("end", lang),
            value=datetime.now(tz=ZoneInfo("Europe/Istanbul")) - timedelta(days=moex_delay),
            max_value=datetime.now(tz=ZoneInfo("Europe/Istanbul")),
            format="DD/MM/YYYY",
        )

    date_valid = start_date < end_date
    if not date_valid:
        render_banner(get_text("date_error", lang), "error-banner")

    st.markdown("---")
    st.markdown(
        f"<p style='color: {COLORS['text_dark']}; font-weight: 600; margin-bottom: 0;'>{get_text('analysis_options', lang)}</p>",
        unsafe_allow_html=True,
    )
    analysis_mode_options = {
        get_text("mode_local", lang): "local",
        get_text("mode_usd", lang): "usd",
        get_text("mode_real", lang): "real",
    }
    selected_analysis_label = st.selectbox(
        get_text("analysis_mode", lang),
        options=list(analysis_mode_options.keys()),
        index=0,
        help=get_text("analysis_mode_help", lang),
    )
    analysis_mode = cast(AnalysisMode, analysis_mode_options[selected_analysis_label])

    st.markdown("---")
    sector_info = SECTORS[selected_sector_id]
    st.markdown(
        f"""
        <div style="background-color: white; padding: 1rem; border-radius: 8px; border: 1px solid #E0E0E0;">
            <p style="color: {COLORS['text_muted']}; font-size: 0.8rem; margin-bottom: 0.5rem;">{get_text("current_pair", lang)}</p>
            <p style="color: {COLORS['text_dark']}; margin: 0.25rem 0;"><strong>🇹🇷 {get_text("turkey", lang)}:</strong> {sector_info['TR']}</p>
            <p style="color: {COLORS['text_dark']}; margin: 0.25rem 0;"><strong>🇷🇺 {get_text("russia", lang)}:</strong> {sector_info['RU']}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.markdown(
        f"""
        <div style="text-align: center; padding: 1rem 0;">
            <p style="color: {COLORS['text_muted']}; font-size: 0.75rem;">
                {get_text("data_source", lang)}<br>
                {get_text("built_with", lang)}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(f'<div class="main-header">{get_text("app_title", lang)}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-header">{get_text("app_subtitle", lang)}</div>', unsafe_allow_html=True)

sector_data = SECTORS[selected_sector_id]
sector_desc = get_text(f"{selected_sector_id}_desc", lang)
st.markdown(
    f"""
    <div style="text-align: center; margin-bottom: 1.5rem;">
        <span style="font-size: 1.5rem; color: {COLORS['primary']}; font-weight: 600;">
            {selected_sector_display}
        </span>
        <span style="color: {COLORS['text_muted']}; margin-left: 0.5rem;">
            — {sector_desc}
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)

if not date_valid:
    st.stop()

with st.spinner(get_text("fetching_data", lang)):
    dashboard_data = load_dashboard_data(sector_data, start_date, end_date, analysis_mode)

render_source_status(dashboard_data.tr_result, sector_data["TR"], lang, "bist_live")
render_source_status(dashboard_data.ru_result, sector_data["RU"], lang, "moex_live")

if dashboard_data.tr_result.is_success and dashboard_data.ru_result.is_success:
    render_general_overview(dashboard_data, sector_data, end_date, lang, analysis_mode=analysis_mode)
    comparison_result = prepare_comparison_series(
        dashboard_data.tr_result,
        dashboard_data.ru_result,
        dashboard_data.usd_rates,
        dashboard_data.inflation_window,
        analysis_mode,
        DATA_CONFIG["min_data_points"],
    )

    if comparison_result.is_success:
        if analysis_mode == "usd" and comparison_result.is_complete:
            render_banner(f"💵 {get_text('usd_conversion_active', lang)}", "success-banner")
        elif (
            analysis_mode == "real"
            and dashboard_data.inflation_window.is_success
            and dashboard_data.inflation_window.payload is not None
            and comparison_result.is_complete
        ):
            base_month = dashboard_data.inflation_window.payload.shared_base_month.strftime("%m/%Y")
            render_banner(
                f"🧮 {get_text('real_conversion_active', lang, base_month=base_month)}",
                "success-banner",
            )
        elif comparison_result.effective_range is not None:
            if analysis_mode == "usd":
                partial_key = "usd_conversion_partial"
            elif analysis_mode == "real":
                partial_key = "real_conversion_partial"
            else:
                partial_key = "comparison_window_partial"

            partial_kwargs = {
                "start_date": comparison_result.effective_range.start.strftime("%d/%m/%Y"),
                "end_date": comparison_result.effective_range.end.strftime("%d/%m/%Y"),
            }
            if (
                analysis_mode == "real"
                and dashboard_data.inflation_window.is_success
                and dashboard_data.inflation_window.payload is not None
            ):
                partial_kwargs["base_month"] = dashboard_data.inflation_window.payload.shared_base_month.strftime("%m/%Y")

            render_banner(
                get_text(partial_key, lang, **partial_kwargs),
                "warning-banner",
            )

    if not comparison_result.is_success:
        if analysis_mode == "usd" and comparison_result.error_code == "conversion_incomplete":
            render_banner(get_text("comparison_window_unavailable", lang), "warning-banner")
        elif analysis_mode == "usd":
            show_error(cast(OperationResult[object], comparison_result), "FX", lang)
        elif analysis_mode == "real" and comparison_result.error_code == "inflation_incomplete":
            render_banner(get_text("real_conversion_unavailable", lang), "warning-banner")
        elif analysis_mode == "local" and comparison_result.error_code == "insufficient_data":
            render_banner(get_text("comparison_window_unavailable_local", lang), "warning-banner")
    else:
        series_pair = comparison_result.payload
        if series_pair is None:
            fallback_key = "comparison_window_unavailable"
            if analysis_mode == "local":
                fallback_key = "comparison_window_unavailable_local"
            if analysis_mode == "real":
                fallback_key = "real_conversion_unavailable"
            render_banner(get_text(fallback_key, lang), "warning-banner")
        else:
            render_current_metrics(series_pair, sector_data, lang)
            render_risk_metrics(series_pair, lang)
            render_chart(series_pair, sector_data, start_date, end_date, lang)
            render_correlation(series_pair, lang)

    render_methodology_card(build_methodology_points(lang), lang)
else:
    st.markdown(
        f"""
        <div style="background-color: #FFF3CD; padding: 2rem; border-radius: 8px; text-align: center; margin: 2rem 0;">
            <h3 style="color: #664D03; margin-bottom: 1rem;">📊 {get_text("no_data_error", lang)}</h3>
            <p style="color: #664D03;">
                {"Try setting the end date to at least 2-3 days ago." if lang == "en" else
                 "Bitiş tarihini en az 2-3 gün öncesine ayarlamayı deneyin." if lang == "tr" else
                 "Попробуйте установить дату окончания как минимум на 2-3 дня назад."}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

render_risk_summary_card(build_risk_summary_items(lang), lang)
st.markdown("---")
st.markdown(
    f"""
    <div style="text-align: center; padding: 1rem 0; color: {COLORS['text_muted']}; font-size: 0.8rem;">
        <p>{get_text("footer_title", lang)}</p>
        <p>{get_text("footer_disclaimer", lang)}</p>
    </div>
    """,
    unsafe_allow_html=True,
)
