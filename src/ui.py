"""
UI components module for The Eurasian Bridge application.
Contains chart creation and styled component rendering functions.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.analysis import interpret_correlation
from src.config import COLORS, get_text
from src.models import OperationResult

logger = logging.getLogger(__name__)


def get_custom_css() -> str:
    """Generate custom CSS for the institutional finance theme."""
    return f"""
    <style>
        /* Main app styling */
        .stApp {{
            background-color: {COLORS['background']};
        }}
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {{
            background-color: {COLORS['card_bg']};
            border-right: 1px solid #E0E0E0;
        }}
        
        [data-testid="stSidebar"] .stMarkdown {{
            color: {COLORS['text_dark']};
        }}
        
        /* Header styling */
        .main-header {{
            font-family: 'Georgia', serif;
            font-size: 2.5rem;
            font-weight: 700;
            color: {COLORS['primary']};
            text-align: center;
            padding: 1rem 0;
            border-bottom: 3px solid {COLORS['primary']};
            margin-bottom: 1rem;
        }}
        
        .sub-header {{
            font-family: 'Arial', sans-serif;
            font-size: 1.1rem;
            color: {COLORS['text_muted']};
            text-align: center;
            margin-bottom: 2rem;
        }}
        
        /* Metric cards */
        .metric-card {{
            background-color: {COLORS['card_bg']};
            border: 1px solid #E0E0E0;
            border-radius: 8px;
            padding: 1.2rem;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        
        .metric-label {{
            font-family: 'Arial', sans-serif;
            font-size: 0.85rem;
            color: {COLORS['text_muted']};
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
        }}
        
        .metric-value {{
            font-family: 'Georgia', serif;
            font-size: 1.8rem;
            font-weight: 700;
            color: {COLORS['text_dark']};
        }}
        
        .metric-change-positive {{
            color: {COLORS['success']};
            font-weight: 600;
        }}
        
        .metric-change-negative {{
            color: {COLORS['danger']};
            font-weight: 600;
        }}
        
        /* Correlation card */
        .correlation-card {{
            background: linear-gradient(135deg, {COLORS['primary']} 0%, #4A1F25 100%);
            border-radius: 12px;
            padding: 2rem;
            text-align: center;
            color: white;
            margin: 1.5rem 0;
        }}
        
        .correlation-title {{
            font-family: 'Arial', sans-serif;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            opacity: 0.9;
            margin-bottom: 0.5rem;
        }}
        
        .correlation-value {{
            font-family: 'Georgia', serif;
            font-size: 3rem;
            font-weight: 700;
        }}
        
        .correlation-interpretation {{
            font-family: 'Arial', sans-serif;
            font-size: 0.95rem;
            opacity: 0.85;
            margin-top: 0.5rem;
        }}
        
        /* Warning banner - High Contrast */
        .warning-banner {{
            background-color: #FFF3CD;
            border: 1px solid #FFE69C;
            border-left: 6px solid #FFC107;
            border-radius: 6px;
            padding: 1rem;
            margin: 1rem 0;
            font-family: 'Arial', sans-serif;
            color: #000000;
            font-weight: 500;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        
        /* Success banner - High Contrast */
        .success-banner {{
            background-color: #D1E7DD;
            border: 1px solid #BADBCC;
            border-left: 6px solid #198754;
            border-radius: 6px;
            padding: 1rem;
            margin: 1rem 0;
            font-family: 'Arial', sans-serif;
            color: #000000;
            font-weight: 500;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        
        /* Error banner - High Contrast */
        .error-banner {{
            background-color: #F8D7DA;
            border: 1px solid #F5C6CB;
            border-left: 6px solid #DC3545;
            border-radius: 6px;
            padding: 1rem;
            margin: 1rem 0;
            font-family: 'Arial', sans-serif;
            color: #000000;
            font-weight: 500;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        
        /* Section headers */
        .section-header {{
            font-family: 'Georgia', serif;
            font-size: 1.3rem;
            color: {COLORS['primary']};
            border-bottom: 2px solid {COLORS['secondary']};
            padding-bottom: 0.5rem;
            margin: 1.5rem 0 1rem 0;
        }}
        
        /* Hide Streamlit branding */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        
        /* Selectbox styling */
        .stSelectbox label {{
            color: {COLORS['text_dark']} !important;
            font-weight: 600;
        }}
    </style>
    """


def create_normalized_chart(tr_data: pd.Series, ru_data: pd.Series,
                            tr_ticker: str, ru_ticker: str, lang: str = "en",
                            currency_label: str = "",
                            macro_events: list[dict[str, object]] | None = None) -> go.Figure:
    """
    Create normalized performance chart with institutional styling.
    
    Args:
        tr_data: Normalized Turkish stock data
        ru_data: Normalized Russian stock data
        tr_ticker: Turkish ticker symbol
        ru_ticker: Russian ticker symbol
        lang: Language code for labels
        currency_label: Currency label (e.g., "USD")
        macro_events: List of macro events to display
    
    Returns:
        Plotly Figure object
    """
    if macro_events is None:
        macro_events = []
    # Build chart title
    if currency_label:
        title = f"{get_text('chart_title', lang)} ({currency_label})"
    else:
        title = get_text("chart_title", lang)
    
    fig = go.Figure()
    
    # Turkish asset line
    fig.add_trace(go.Scatter(
        x=tr_data.index,
        y=tr_data.values,
        name=f"🇹🇷 {tr_ticker}",
        line=dict(color=COLORS['tr_line'], width=2.5),
        hovertemplate='%{x|%b %d, %Y}<br>Value: %{y:.2f}<extra></extra>'
    ))
    
    # Russian asset line
    fig.add_trace(go.Scatter(
        x=ru_data.index,
        y=ru_data.values,
        name=f"🇷🇺 {ru_ticker}",
        line=dict(color=COLORS['ru_line'], width=2.5),
        hovertemplate='%{x|%b %d, %Y}<br>Value: %{y:.2f}<extra></extra>'
    ))
    
    # Reference line at 100
    fig.add_hline(
        y=100, 
        line_dash="dash", 
        line_color="#CCCCCC",
        annotation_text=get_text("base_label", lang),
        annotation_position="right"
    )
    
    # Layout with institutional styling
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(family="Georgia, serif", size=18, color=COLORS['text_dark']),
            x=0.5,
            xanchor='center'
        ),
        xaxis=dict(
            title=dict(
                text=get_text("date_axis", lang),
                font=dict(family="Arial, sans-serif", size=12, color=COLORS['text_muted'])
            ),
            tickfont=dict(family="Arial, sans-serif", size=10, color=COLORS['text_dark']),
            gridcolor='#E0E0E0',
            showgrid=True,
            zeroline=False
        ),
        yaxis=dict(
            title=dict(
                text=get_text("value_axis", lang),
                font=dict(family="Arial, sans-serif", size=12, color=COLORS['text_muted'])
            ),
            tickfont=dict(family="Arial, sans-serif", size=10, color=COLORS['text_dark']),
            gridcolor='#E0E0E0',
            showgrid=True,
            zeroline=False
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(family="Arial, sans-serif", size=11)
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='x unified',
        margin=dict(l=60, r=40, t=80, b=60),
        height=450
    )
    
    # Add vertical lines for macro events
    for event in macro_events:
        try:
            # Convert to Python datetime for plotly
            event_date = event["date"]
            if isinstance(event_date, pd.Timestamp):
                event_date = event_date.to_pydatetime()
            elif isinstance(event_date, datetime):
                pass
            elif isinstance(event_date, date):
                event_date = datetime.combine(event_date, datetime.min.time())
            else:
                raise ValueError("Unsupported event date type")
            
            event_type = event.get('type', 'other')
            
            # Color based on event type
            if event_type == 'interest_rate':
                line_color = '#FF6B6B'  # Red for interest rate
            elif event_type == 'inflation':
                line_color = '#FFA500'  # Orange for inflation
            elif event_type == 'crisis':
                line_color = '#DC3545'  # Dark red for crisis
            else:
                line_color = '#6C757D'  # Grey for other
            
            fig.add_vline(
                x=event_date,
                line_dash="dot",
                line_color=line_color,
                annotation_text=event['title'],
                annotation_position="top",
                annotation_font_size=9,
                annotation_font_color=line_color
            )
        except Exception as exc:
            logger.warning("Skipping macro event that could not be plotted: %s", exc)
    
    return fig


def format_metric_value(
    value: float | Decimal | None,
    lang: str,
    *,
    decimals: int = 1,
    prefix: str = "",
    suffix: str = "",
    signed: bool = False,
) -> str:
    """Format a metric value for display or return the localized unavailable text."""

    if value is None:
        return get_text("metric_unavailable", lang)

    sign = "+" if signed and value >= 0 else ""
    return f"{prefix}{sign}{value:,.{decimals}f}{suffix}"


def render_metric_card(
    label: str,
    value: str,
    change: float | None = None,
    is_currency: bool = False,
    help_text: str | None = None,
) -> None:
    """
    Render a styled metric card.
    
    Args:
        label: Card label text
        value: Main value to display
        change: Optional percentage change value
        is_currency: Whether the value is a currency (unused, kept for API compatibility)
        help_text: Optional help text shown below the value
    """
    change_html = ""
    if change is not None:
        change_class = "metric-change-positive" if change >= 0 else "metric-change-negative"
        change_symbol = "▲" if change >= 0 else "▼"
        change_html = f'<div class="{change_class}">{change_symbol} {abs(change):.2f}%</div>'
    
    help_html = ""
    if help_text:
        help_html = f'<p style="font-size: 0.7rem; color: #666; margin-top: 0.5rem; border-top: 1px solid #eee; padding-top: 0.25rem; margin-bottom: 0;">{help_text}</p>'
    
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f'{change_html}'
        f'{help_html}'
        f'</div>',
        unsafe_allow_html=True
    )


def render_correlation_card(correlation: float, lang: str = "en") -> None:
    """
    Render the correlation coefficient in a styled card.
    
    Args:
        correlation: Pearson correlation coefficient
        lang: Language code for translation
    """
    interpretation = interpret_correlation(correlation, lang)
    corr_display = f"{correlation:.3f}" if not np.isnan(correlation) else "N/A"
    
    st.markdown(f"""
    <div class="correlation-card">
        <div class="correlation-title">{get_text("pearson_correlation", lang)}</div>
        <div class="correlation-value">{corr_display}</div>
        <div class="correlation-interpretation">{interpretation}</div>
    </div>
    """, unsafe_allow_html=True)


def render_market_cap_card(
    tr_cap: float | None,
    ru_cap: float | None,
    lang: str = "en",
    source_note: str | None = None
) -> None:
    """Render Market Cap Comparison Card."""

    unavailable_text = get_text("metric_unavailable", lang)
    tr_display = unavailable_text
    ru_display = unavailable_text
    comparison_text = get_text("market_cap_unavailable", lang)
    if tr_cap is not None:
        tr_display = f"${tr_cap:.1f}B"
    if ru_cap is not None:
        ru_display = f"${ru_cap:.1f}B"

    if tr_cap is not None and ru_cap is not None and tr_cap > 0 and ru_cap > 0:
        if ru_cap >= tr_cap:
            comparison_text = get_text(
                "market_cap_leader",
                lang,
                market=get_text("russia", lang),
                multiple=f"{ru_cap / tr_cap:.1f}x"
            )
        else:
            comparison_text = get_text(
                "market_cap_leader",
                lang,
                market=get_text("turkey", lang),
                multiple=f"{tr_cap / ru_cap:.1f}x"
            )

    source_html = ""
    if source_note:
        source_html = (
            f'<div style="margin-top: 0.65rem; text-align: center; font-size: 0.72rem; '
            f'color: {COLORS["text_muted"]};">{source_note}</div>'
        )

    title = get_text("market_cap_comparison", lang)
    turkey_label = get_text("turkey", lang)
    russia_label = get_text("russia", lang)

    st.markdown(f"""
    <div style="background-color: {COLORS['card_bg']}; padding: 1rem; border-radius: 8px; border: 1px solid #E0E0E0; margin-bottom: 1rem;">
        <h5 style="color: {COLORS['text_muted']}; margin-bottom: 0.5rem; font-size: 0.9rem;">🏛️ {title}</h5>
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="text-align: center;">
                <div style="font-size: 1.2rem; font-weight: bold; color: {COLORS['tr_line']};">{tr_display}</div>
                <div style="font-size: 0.7rem; color: {COLORS['text_muted']};">{turkey_label}</div>
            </div>
            <div style="font-size: 0.9rem; font-weight: bold; color: {COLORS['text_dark']}; padding: 0 0.5rem;">vs</div>
            <div style="text-align: center;">
                <div style="font-size: 1.2rem; font-weight: bold; color: {COLORS['ru_line']};">{ru_display}</div>
                <div style="font-size: 0.7rem; color: {COLORS['text_muted']};">{russia_label}</div>
            </div>
        </div>
        <div style="margin-top: 0.5rem; text-align: center; font-size: 0.8rem; color: {COLORS['text_dark']};">
            {comparison_text}
        </div>
        {source_html}
    </div>
    """, unsafe_allow_html=True)


def render_ytd_card(
    tr_ytd: float | None,
    ru_ytd: float | None,
    tr_ticker: str,
    ru_ticker: str,
    year: int,
    lang: str = "en"
) -> None:
    """Render YTD Performance Card."""

    neutral_color = COLORS["text_muted"]
    tr_color = neutral_color if tr_ytd is None else COLORS["success"] if tr_ytd >= 0 else COLORS["danger"]
    ru_color = neutral_color if ru_ytd is None else COLORS["success"] if ru_ytd >= 0 else COLORS["danger"]
    tr_display = format_metric_value(tr_ytd, lang, decimals=1, suffix="%", signed=True)
    ru_display = format_metric_value(ru_ytd, lang, decimals=1, suffix="%", signed=True)

    if tr_ytd is None or ru_ytd is None:
        winner = get_text("metric_unavailable", lang)
    elif tr_ytd == ru_ytd:
        winner = get_text("tie_label", lang)
    elif tr_ytd > ru_ytd:
        winner = get_text("turkey", lang)
    else:
        winner = get_text("russia", lang)

    title = get_text("ytd_performance", lang, year=year)
    leader_text = get_text("leader_label", lang)

    st.markdown(f"""
    <div style="background-color: {COLORS['card_bg']}; padding: 1rem; border-radius: 8px; border: 1px solid #E0E0E0; margin-bottom: 1rem;">
        <h5 style="color: {COLORS['text_muted']}; margin-bottom: 0.5rem; font-size: 0.9rem;">🏆 {title}</h5>
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="text-align: center;">
                <div style="font-size: 1.1rem; font-weight: bold; color: {tr_color};">{tr_display}</div>
                <div style="font-size: 0.7rem; color: {COLORS['text_muted']};">{tr_ticker}</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 1.1rem; font-weight: bold; color: {ru_color};">{ru_display}</div>
                <div style="font-size: 0.7rem; color: {COLORS['text_muted']};">{ru_ticker}</div>
            </div>
        </div>
        <div style="margin-top: 0.5rem; text-align: center; font-size: 0.8rem; color: {COLORS['text_dark']}; font-weight: bold;">
            {leader_text}: {winner}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_methodology_card(points: list[str], lang: str = "en") -> None:
    """Render the methodology and limitations section."""

    bullet_items = "".join(
        f"<li style='margin-bottom: 0.55rem;'>{point}</li>"
        for point in points
    )

    st.markdown(f"""
    <div style="background-color: {COLORS['card_bg']}; padding: 1.5rem; border-radius: 8px; margin-top: 1rem;">
        <h4 style="color: {COLORS['primary']}; font-family: Georgia, serif; margin-bottom: 1rem;">
            {get_text("methodology_title", lang)}
        </h4>
        <ul style="color: {COLORS['text_dark']}; font-family: Arial, sans-serif; font-size: 0.9rem; line-height: 1.6; padding-left: 1.2rem; margin: 0;">
            {bullet_items}
        </ul>
    </div>
    """, unsafe_allow_html=True)


def render_risk_summary_card(items: list[tuple[str, str]], lang: str = "en") -> None:
    """Render a localized quick guide for the displayed risk metrics."""

    summary_items = "".join(
        f"<li style='margin-bottom: 0.6rem;'><strong>{label}:</strong> {summary}</li>"
        for label, summary in items
    )

    st.markdown(f"""
    <div style="background-color: {COLORS['card_bg']}; padding: 1.5rem; border-radius: 8px; margin-top: 1.5rem; border: 1px solid #E0E0E0;">
        <h4 style="color: {COLORS['primary']}; font-family: Georgia, serif; margin-bottom: 0.75rem;">
            {get_text("risk_summary_title", lang)}
        </h4>
        <p style="color: {COLORS['text_dark']}; font-family: Arial, sans-serif; font-size: 0.92rem; line-height: 1.65; margin-bottom: 0.9rem;">
            {get_text("risk_summary_intro", lang)}
        </p>
        <ul style="color: {COLORS['text_dark']}; font-family: Arial, sans-serif; font-size: 0.9rem; line-height: 1.6; padding-left: 1.2rem; margin: 0;">
            {summary_items}
        </ul>
    </div>
    """, unsafe_allow_html=True)



def show_error(result: OperationResult[object], ticker: str, lang: str) -> None:
    """
    Display an error banner based on the error code in the result.
    
    Args:
        result: Data fetch result dictionary
        ticker: Ticker symbol for error message
        lang: Language code for translation
    """
    error_code = result.error_code
    msg = ""
    if error_code == 'timeout':
        msg = get_text("error_timeout", lang)
    elif error_code == 'connection':
        msg = get_text("error_connection", lang)
    elif error_code == 'schema_error':
        msg = get_text("error_schema", lang)
    elif error_code == 'no_data':
        msg = get_text("error_no_data", lang, ticker=ticker)
    elif error_code == 'insufficient_data':
        msg = get_text("error_insufficient", lang, ticker=ticker)
    elif error_code == 'unsupported_window':
        msg = get_text("error_unsupported_window", lang)
    elif error_code == 'conversion_incomplete':
        msg = get_text("error_conversion_incomplete", lang)
    elif error_code == 'inflation_incomplete':
        msg = get_text("error_inflation_incomplete", lang)
    else:
        msg = get_text("data_unavailable", lang, ticker=ticker)
    
    st.markdown(f'<div class="error-banner">{msg}</div>', unsafe_allow_html=True)
