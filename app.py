"""
The Eurasian Bridge: BIST vs. MOEX Analyzer
A Streamlit application for analyzing Turkish and Russian stock market sectors.

This is the main entry point. All logic is organized into modules under src/.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal

import numpy as np
import streamlit as st

from src.config import (
    SECTORS, COLORS, APP_CONFIG, DATA_CONFIG,
    LANGUAGE_OPTIONS, MARKET_CAP_METADATA, get_text, get_sector_options,
    get_macro_events_in_range
)
from src.data import (
    convert_to_usd, fetch_market_cap_async, fetch_stock_data_async,
    fetch_usd_rates_async, fetch_ytd_start_price
)
from src.analysis import (
    calculate_cagr, calculate_change_pct, calculate_correlation,
    calculate_maximum_drawdown, calculate_sharpe_ratio, calculate_volatility,
    normalize_to_base_100
)
from src.ui import (
    create_normalized_chart, get_custom_css, render_correlation_card,
    render_market_cap_card, render_methodology_card, render_metric_card,
    render_ytd_card, show_error
)


def calculate_ytd_change(result: dict, start_price: Decimal) -> float:
    """Calculate YTD change using the fetched first-trading-day price."""

    price_frame = result.get("df")
    if not result.get("success") or price_frame is None or price_frame.empty or start_price <= 0:
        return 0.0

    current_price = Decimal(str(price_frame.iloc[-1]["Close"]))
    return float((current_price - start_price) / start_price * Decimal("100"))


async def fetch_dashboard_payload(
    sector_data: dict,
    start_date: date,
    end_date: date,
    include_usd: bool
) -> list[object]:
    """Fetch all remote data needed to render the dashboard."""

    tasks: list[object] = [
        fetch_stock_data_async(sector_data["TR"], start_date, end_date, is_russian=False),
        fetch_stock_data_async(sector_data["RU"], start_date, end_date, is_russian=True),
        fetch_market_cap_async(sector_data["TR"], is_russian=False),
        fetch_market_cap_async(sector_data["RU"], is_russian=True),
        fetch_ytd_start_price(sector_data["TR"], is_russian=False),
        fetch_ytd_start_price(sector_data["RU"], is_russian=True),
    ]

    if include_usd:
        tasks.append(fetch_usd_rates_async(start_date, end_date))

    return await asyncio.gather(*tasks)


def load_dashboard_data(
    sector_data: dict,
    start_date: date,
    end_date: date,
    include_usd: bool
) -> dict[str, object]:
    """Run async data collection and normalize the result structure."""

    try:
        results = asyncio.run(
            fetch_dashboard_payload(sector_data, start_date, end_date, include_usd)
        )
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            results = loop.run_until_complete(
                fetch_dashboard_payload(sector_data, start_date, end_date, include_usd)
            )
        finally:
            loop.close()

    usd_rates = results[6] if include_usd else {"success": False, "complete": False}
    return {
        "tr_result": results[0],
        "ru_result": results[1],
        "tr_cap": results[2],
        "ru_cap": results[3],
        "tr_ytd_start": results[4],
        "ru_ytd_start": results[5],
        "usd_rates": usd_rates,
    }


def has_complete_usd_rates(usd_rates: dict) -> bool:
    """Return True when both TRY and RUB FX series are available."""

    return bool(
        usd_rates.get("complete")
        or (
            usd_rates.get("USD_TRY") is not None
            and usd_rates.get("USD_RUB") is not None
        )
    )


def get_currency_labels(is_usd_conversion_active: bool) -> tuple[str, str, str]:
    """Return price labels for the current display mode."""

    if is_usd_conversion_active:
        return "$", "$", "USD"

    return "₺", "₽", ""


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
    ]



# ============================================================================
# PAGE CONFIGURATION & STYLING
# ============================================================================

st.set_page_config(
    page_title=f"{APP_CONFIG['title']} v2.0",
    page_icon=APP_CONFIG["icon"],
    layout=APP_CONFIG["layout"],
    initial_sidebar_state=APP_CONFIG["sidebar_state"]
)

# Apply custom CSS
st.markdown(get_custom_css(), unsafe_allow_html=True)


# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    # Language selector at the top
    st.markdown("""
    <div style="text-align: center; padding: 0.5rem 0;">
        <span style="font-size: 2.5rem;">🌉</span>
    </div>
    """, unsafe_allow_html=True)
    
    selected_language = st.selectbox(
        "🌐 Language / Dil / Язык",
        options=list(LANGUAGE_OPTIONS.keys()),
        index=0
    )
    lang = LANGUAGE_OPTIONS[selected_language]
    
    st.markdown(f"""
    <div style="text-align: center; padding: 0.5rem 0;">
        <h2 style="color: {COLORS['primary']}; font-family: Georgia, serif; margin: 0.5rem 0;">
            {get_text("sector_analysis", lang)}
        </h2>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Sector selection - get localized options
    sector_options = get_sector_options(lang)
    selected_sector_display = st.selectbox(
        get_text("select_sector", lang),
        options=list(sector_options.keys()),
        index=0,
        help=get_text("sector_help", lang)
    )
    # Get the sector ID from the display name
    selected_sector_id = sector_options[selected_sector_display]
    
    st.markdown("---")
    
    # Date range
    st.markdown(f"<p style='color: {COLORS['text_dark']}; font-weight: 600;'>{get_text('analysis_period', lang)}</p>", 
                unsafe_allow_html=True)
    
    moex_delay = DATA_CONFIG["moex_delay_days"]
    default_lookback = DATA_CONFIG["default_lookback_days"]
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            get_text("start", lang),
            value=datetime.now() - timedelta(days=default_lookback),
            max_value=datetime.now(),
            format="DD/MM/YYYY"
        )
    with col2:
        end_date = st.date_input(
            get_text("end", lang),
            value=datetime.now() - timedelta(days=moex_delay),
            max_value=datetime.now(),
            format="DD/MM/YYYY"
        )
    
    # Date validation
    date_valid = True
    if start_date >= end_date:
        date_valid = False
        st.markdown(
            f'<div class="error-banner">{get_text("date_error", lang)}</div>',
            unsafe_allow_html=True
        )
    
    st.markdown("---")
    
    # Currency toggle with enhanced styling
    st.markdown(f"<p style='color: {COLORS['text_dark']}; font-weight: 600; margin-bottom: 0;'>{get_text('analysis_options', lang)}</p>", 
                unsafe_allow_html=True)
    
    show_usd = st.checkbox(
        get_text("show_usd", lang),
        value=False,
        help=get_text("show_usd_help", lang)
    )
    
    st.markdown("---")
    
    # Sector info
    sector_info = SECTORS[selected_sector_id]
    st.markdown(f"""
    <div style="background-color: white; padding: 1rem; border-radius: 8px; border: 1px solid #E0E0E0;">
        <p style="color: {COLORS['text_muted']}; font-size: 0.8rem; margin-bottom: 0.5rem;">{get_text("current_pair", lang)}</p>
        <p style="color: {COLORS['text_dark']}; margin: 0.25rem 0;"><strong>🇹🇷 {get_text("turkey", lang)}:</strong> {sector_info['TR']}</p>
        <p style="color: {COLORS['text_dark']}; margin: 0.25rem 0;"><strong>🇷🇺 {get_text("russia", lang)}:</strong> {sector_info['RU']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown(f"""
    <div style="text-align: center; padding: 1rem 0;">
        <p style="color: {COLORS['text_muted']}; font-size: 0.75rem;">
            {get_text("data_source", lang)}<br>
            {get_text("built_with", lang)}
        </p>
    </div>
    """, unsafe_allow_html=True)


# ============================================================================
# MAIN CONTENT
# ============================================================================

# Header
st.markdown(f'<div class="main-header">{get_text("app_title", lang)}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-header">{get_text("app_subtitle", lang)}</div>', 
            unsafe_allow_html=True)

# Sector description
sector_data = SECTORS[selected_sector_id]
sector_desc = get_text(f"{selected_sector_id}_desc", lang)
st.markdown(f"""
<div style="text-align: center; margin-bottom: 1.5rem;">
    <span style="font-size: 1.5rem; color: {COLORS['primary']}; font-weight: 600;">
        {selected_sector_display}
    </span>
    <span style="color: {COLORS['text_muted']}; margin-left: 0.5rem;">
        — {sector_desc}
    </span>
</div>
""", unsafe_allow_html=True)

# Stop here if dates are invalid
if not date_valid:
    st.stop()

# Fetch data
with st.spinner(get_text("fetching_data", lang)):
    dashboard_data = load_dashboard_data(sector_data, start_date, end_date, show_usd)

tr_result = dashboard_data["tr_result"]
ru_result = dashboard_data["ru_result"]
tr_cap = dashboard_data["tr_cap"]
ru_cap = dashboard_data["ru_cap"]
tr_ytd_start = dashboard_data["tr_ytd_start"]
ru_ytd_start = dashboard_data["ru_ytd_start"]
usd_rates = dashboard_data["usd_rates"]
tr_ytd = calculate_ytd_change(tr_result, tr_ytd_start)
ru_ytd = calculate_ytd_change(ru_result, ru_ytd_start)

# Extract data
tr_df = tr_result['df']
ru_df = ru_result['df']

# Check transparency
tr_has_data = tr_result['success']
ru_has_data = ru_result['success']

# Display status banners
if tr_has_data:
    st.markdown(f"""
    <div class="success-banner">
        {get_text("bist_live", lang)} ({sector_data['TR']})
    </div>
    """, unsafe_allow_html=True)
    
    if tr_result['date_adjusted']:
        msg = get_text("date_adjusted", lang, 
                      actual_date=tr_result['actual_end_date'].strftime('%d/%m/%Y'),
                      requested_date=tr_result['requested_end_date'].strftime('%d/%m/%Y'))
        st.markdown(f'<div class="warning-banner">{msg}</div>', unsafe_allow_html=True)

if ru_has_data:
    st.markdown(f"""
    <div class="success-banner">
        {get_text("moex_live", lang)} ({sector_data['RU']})
    </div>
    """, unsafe_allow_html=True)
    
    if ru_result['date_adjusted']:
        msg = get_text("date_adjusted", lang, 
                      actual_date=ru_result['actual_end_date'].strftime('%d/%m/%Y'),
                      requested_date=ru_result['requested_end_date'].strftime('%d/%m/%Y'))
        st.markdown(f'<div class="warning-banner">{msg}</div>', unsafe_allow_html=True)

# Show error messages for unavailable data
if not tr_has_data:
    show_error(tr_result, sector_data['TR'], lang)
    
if not ru_has_data:
    show_error(ru_result, sector_data['RU'], lang)

# Only show analysis if we have data from both sources
if tr_has_data and ru_has_data:
    is_usd_conversion_active = False
    if show_usd and has_complete_usd_rates(usd_rates):
        converted_tr = convert_to_usd(tr_df['Close'], 'TRY', usd_rates)
        converted_ru = convert_to_usd(ru_df['Close'], 'RUB', usd_rates)

        if not converted_tr.empty and not converted_ru.empty:
            tr_df_usd = converted_tr
            ru_df_usd = converted_ru
            is_usd_conversion_active = True

    if is_usd_conversion_active:
        st.markdown(f"""
        <div class="success-banner">
            💵 {get_text("usd_conversion_active", lang)}
        </div>
        """, unsafe_allow_html=True)
    else:
        tr_df_usd = tr_df['Close']
        ru_df_usd = ru_df['Close']
        if show_usd:
            st.markdown(f"""
            <div class="warning-banner">
                {get_text("usd_conversion_unavailable", lang)}
            </div>
            """, unsafe_allow_html=True)
    
    # ============================================================================
    # GENERAL INFO METRICS (PHASE 4)
    # ============================================================================
    
    st.markdown(f'<div class="section-header">🌍 {get_text("general_overview", lang) if lang != "en" else "General Overview"}</div>', unsafe_allow_html=True)
    
    col_ytd, col_cap = st.columns(2)
    
    with col_ytd:
        render_ytd_card(
            tr_ytd,
            ru_ytd,
            sector_data['TR'],
            sector_data['RU'],
            year=datetime.now().year,
            lang=lang
        )
        
    with col_cap:
        render_market_cap_card(
            tr_cap,
            ru_cap,
            lang,
            source_note=build_market_cap_source_note(lang)
        )

    # ============================================================================
    # METRICS ROW
    # ============================================================================
    
    # Determine currency symbol and labels
    tr_currency, ru_currency, currency_label = get_currency_labels(is_usd_conversion_active)
    
    st.markdown(f'<div class="section-header">{get_text("current_metrics", lang)}</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        tr_price = tr_df_usd.iloc[-1]
        tr_change = calculate_change_pct(tr_df_usd)
        render_metric_card(
            f"🇹🇷 {sector_data['TR']}",
            f"{tr_currency}{tr_price:,.2f}",
            tr_change
        )

    with col2:
        tr_start_date = tr_df_usd.index[0].strftime('%d/%m/%Y')
        tr_start_price = tr_df_usd.iloc[0]
        render_metric_card(
            get_text("tr_period_change", lang),
            f"{tr_change:+.2f}%",
            None,
            help_text=get_text("start_price_label", lang, currency=tr_currency, price=f"{tr_start_price:,.2f}", date=tr_start_date)
        )

    with col3:
        ru_price = ru_df_usd.iloc[-1]
        ru_change = calculate_change_pct(ru_df_usd)
        render_metric_card(
            f"🇷🇺 {sector_data['RU']}",
            f"{ru_currency}{ru_price:,.2f}",
            ru_change
        )

    with col4:
        ru_start_date = ru_df_usd.index[0].strftime('%d/%m/%Y')
        ru_start_price = ru_df_usd.iloc[0]
        render_metric_card(
            get_text("ru_period_change", lang),
            f"{ru_change:+.2f}%",
            None,
            help_text=get_text("start_price_label", lang, currency=ru_currency, price=f"{ru_start_price:,.2f}", date=ru_start_date)
        )

    # ============================================================================
    # RISK METRICS
    # ============================================================================
    
    st.markdown(f'<div class="section-header">{get_text("risk_metrics", lang)}</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        tr_volatility = calculate_volatility(tr_df_usd)
        vol_display = f"{tr_volatility:.1f}%" if not np.isnan(tr_volatility) else "N/A"
        render_metric_card(
            get_text("volatility", lang),
            vol_display,
            None
        )
    
    with col2:
        tr_sharpe = calculate_sharpe_ratio(tr_df_usd)
        sharpe_display = f"{tr_sharpe:.2f}" if not np.isnan(tr_sharpe) else "N/A"
        render_metric_card(
            get_text("sharpe_ratio", lang),
            sharpe_display,
            None
        )
    
    with col3:
        ru_volatility = calculate_volatility(ru_df_usd)
        vol_display_ru = f"{ru_volatility:.1f}%" if not np.isnan(ru_volatility) else "N/A"
        render_metric_card(
            get_text("volatility", lang),
            vol_display_ru,
            None
        )
    
    with col4:
        ru_sharpe = calculate_sharpe_ratio(ru_df_usd)
        sharpe_display_ru = f"{ru_sharpe:.2f}" if not np.isnan(ru_sharpe) else "N/A"
        render_metric_card(
            get_text("sharpe_ratio", lang),
            sharpe_display_ru,
            None
        )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        tr_max_drawdown = calculate_maximum_drawdown(tr_df_usd)
        max_drawdown_display = (
            f"{tr_max_drawdown:.1f}%"
            if not np.isnan(tr_max_drawdown)
            else "N/A"
        )
        render_metric_card(
            get_text("max_drawdown", lang),
            max_drawdown_display,
            None
        )

    with col2:
        tr_cagr = calculate_cagr(tr_df_usd)
        tr_cagr_display = f"{tr_cagr:.1f}%" if not np.isnan(tr_cagr) else "N/A"
        render_metric_card(
            get_text("cagr", lang),
            tr_cagr_display,
            None
        )

    with col3:
        ru_max_drawdown = calculate_maximum_drawdown(ru_df_usd)
        ru_max_drawdown_display = (
            f"{ru_max_drawdown:.1f}%"
            if not np.isnan(ru_max_drawdown)
            else "N/A"
        )
        render_metric_card(
            get_text("max_drawdown", lang),
            ru_max_drawdown_display,
            None
        )

    with col4:
        ru_cagr = calculate_cagr(ru_df_usd)
        ru_cagr_display = f"{ru_cagr:.1f}%" if not np.isnan(ru_cagr) else "N/A"
        render_metric_card(
            get_text("cagr", lang),
            ru_cagr_display,
            None
        )

    # ============================================================================
    # NORMALIZED PERFORMANCE CHART
    # ============================================================================

    st.markdown(f'<div class="section-header">{get_text("normalized_performance", lang)}</div>', unsafe_allow_html=True)

    # Normalize data
    tr_normalized = normalize_to_base_100(tr_df_usd)
    ru_normalized = normalize_to_base_100(ru_df_usd)

    # Get macro events for chart annotations
    macro_events = get_macro_events_in_range(start_date, end_date, lang)
    
    # Create and display chart
    fig = create_normalized_chart(
        tr_normalized, ru_normalized,
        sector_data['TR'], sector_data['RU'],
        lang,
        currency_label=currency_label,
        macro_events=macro_events
    )
    st.plotly_chart(fig, width='stretch')

    # ============================================================================
    # CORRELATION ANALYSIS
    # ============================================================================

    st.markdown(f'<div class="section-header">{get_text("correlation_analysis", lang)}</div>', unsafe_allow_html=True)

    # Calculate correlation on returns (more statistically meaningful)
    tr_returns = tr_df_usd.pct_change().dropna()
    ru_returns = ru_df_usd.pct_change().dropna()
    correlation = calculate_correlation(tr_returns, ru_returns)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        render_correlation_card(correlation, lang)

    # Additional analysis context
    st.markdown(f"""
    <div style="background-color: {COLORS['card_bg']}; padding: 1.5rem; border-radius: 8px; margin-top: 1rem;">
        <h4 style="color: {COLORS['primary']}; font-family: Georgia, serif; margin-bottom: 1rem;">
            {get_text("interpretation_guide", lang)}
        </h4>
        <p style="color: {COLORS['text_dark']}; font-family: Arial, sans-serif; font-size: 0.9rem; line-height: 1.6;">
            {get_text("interpretation_text", lang)}
        </p>
    </div>
    """, unsafe_allow_html=True)

    render_methodology_card(build_methodology_points(lang), lang)

else:
    # Show helpful message when data is missing
    st.markdown(f"""
    <div style="background-color: #FFF3CD; padding: 2rem; border-radius: 8px; text-align: center; margin: 2rem 0;">
        <h3 style="color: #664D03; margin-bottom: 1rem;">📊 {get_text("no_data_error", lang)}</h3>
        <p style="color: #664D03;">
            {"Try setting the end date to at least 2-3 days ago." if lang == "en" else 
             "Bitiş tarihini en az 2-3 gün öncesine ayarlamayı deneyin." if lang == "tr" else
             "Попробуйте установить дату окончания как минимум на 2-3 дня назад."}
        </p>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; padding: 1rem 0; color: {COLORS['text_muted']}; font-size: 0.8rem;">
    <p>{get_text("footer_title", lang)}</p>
    <p>{get_text("footer_disclaimer", lang)}</p>
</div>
""", unsafe_allow_html=True)
