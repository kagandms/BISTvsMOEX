"""
Data fetching module for The Eurasian Bridge application.
Handles Finam Export API (for Russian stocks) and Yahoo Finance (for Turkish stocks) data retrieval.
"""

from __future__ import annotations

import io
import logging
import time
from datetime import datetime
from decimal import Decimal, InvalidOperation

import asyncio
import aiohttp
import pandas as pd
import requests
import streamlit as st
import yfinance as yf

from src.config import API_CONFIG, DATA_CONFIG, CACHE_CONFIG, SECTORS, MARKET_CAPS

logger = logging.getLogger(__name__)


@st.cache_data(ttl=CACHE_CONFIG["ttl_seconds"])
def fetch_usd_rates(start_date: datetime, end_date: datetime) -> dict:
    """
    Fetch USD/TRY and USD/RUB exchange rates from Yahoo Finance.
    
    Args:
        start_date: Start date for data retrieval
        end_date: End date for data retrieval
    
    Returns:
        Dict with 'USD_TRY' and 'USD_RUB' DataFrames, or None if unavailable
    """
    result = {
        'USD_TRY': None,
        'USD_RUB': None,
        'success': False,
        'complete': False
    }
    
    try:
        # Fetch USD/TRY
        try:
            usd_try = yf.Ticker("TRY=X")
            df_try = usd_try.history(start=start_date, end=end_date)
            if not df_try.empty:
                df_try = df_try[['Close']].copy()
                df_try.columns = ['USD_TRY']
                df_try.index = df_try.index.tz_localize(None)
                result['USD_TRY'] = df_try
        except Exception as e:
            logger.warning("Failed to fetch USD/TRY: %s", str(e))
        
        # Fetch USD/RUB
        try:
            usd_rub = yf.Ticker("RUB=X")
            df_rub = usd_rub.history(start=start_date, end=end_date)
            if not df_rub.empty:
                df_rub = df_rub[['Close']].copy()
                df_rub.columns = ['USD_RUB']
                df_rub.index = df_rub.index.tz_localize(None)
                result['USD_RUB'] = df_rub
        except Exception as e:
            logger.warning("Failed to fetch USD/RUB: %s", str(e))
        
        has_try_rate = result['USD_TRY'] is not None
        has_rub_rate = result['USD_RUB'] is not None
        result['success'] = has_try_rate or has_rub_rate
        result['complete'] = has_try_rate and has_rub_rate
        return result
        
    except Exception as e:
        logger.exception("Error fetching USD rates")
        return result

@st.cache_data(ttl=CACHE_CONFIG["ttl_seconds"])
def convert_to_usd(df: pd.Series, currency_code: str, usd_rates: dict) -> pd.Series:
    """
    Convert a price series to USD using exchange rates with Decimal precision.
    
    Args:
        df: Price series in original currency
        currency_code: 'TRY' or 'RUB'
        usd_rates: Dict with USD_TRY and USD_RUB DataFrames
    
    Returns:
        Price series converted to USD (as Decimal objects for precision)
    """
    target_rate_df = None
    if currency_code == 'TRY':
        target_rate_df = usd_rates.get('USD_TRY')
    elif currency_code == 'RUB':
        target_rate_df = usd_rates.get('USD_RUB')
    
    if target_rate_df is None:
        return df

    rate_col = target_rate_df.columns[0]
    aligned_rates = target_rate_df.reindex(df.index).ffill()
    aligned = df.to_frame('price').join(aligned_rates, how='left')
    aligned = aligned.dropna(subset=[rate_col])

    if aligned.empty:
        return df.iloc[0:0]
    
    # Define precision conversion function
    def precise_div(row):
        try:
            # Convert both operands to Decimal from string representation
            # This avoids floating point artifacts before the division
            p = Decimal(str(row['price']))
            r = Decimal(str(row[rate_col]))
            
            if r == 0:
                return Decimal('0')
                
            return p / r
        except (InvalidOperation, TypeError, ValueError):
            return Decimal('NaN')

    # Apply row-wise (slower but precise)
    return aligned.apply(precise_div, axis=1)



from src.exceptions import DataSourceError, UpstreamTimeoutError, UpstreamConnectionError

def _build_finam_url(ticker: str, em: int, start_date: datetime, end_date: datetime) -> str:
    """
    Build Finam Export API URL for fetching daily OHLCV data.
    
    Args:
        ticker: MOEX ticker symbol (e.g., 'SBER')
        em: Finam emitent ID
        start_date: Start date
        end_date: End date
    
    Returns:
        Fully constructed Finam export URL
    """
    base_url = API_CONFIG["finam"]["base_url"]
    
    # Format dates for Finam
    df_day = start_date.day
    mf_month = start_date.month - 1  # Finam uses 0-indexed months
    yf_year = start_date.year
    dt_day = end_date.day
    mt_month = end_date.month - 1
    yt_year = end_date.year
    
    from_str = start_date.strftime('%d.%m.%Y')
    to_str = end_date.strftime('%d.%m.%Y')
    
    filename = f"{ticker}_{start_date.strftime('%y%m%d')}_{end_date.strftime('%y%m%d')}"
    
    params = (
        f"/{filename}.csv?"
        f"market=1&em={em}&code={ticker}&apply=0"
        f"&df={df_day}&mf={mf_month}&yf={yf_year}&from={from_str}"
        f"&dt={dt_day}&mt={mt_month}&yt={yt_year}&to={to_str}"
        f"&p=8&f={filename}&e=.csv&cn={ticker}"
        f"&dtf=1&tmf=1&MSOR=1&mstime=on&mstimever=1"
        f"&sep=1&sep2=1&datf=1&at=1"
    )
    
    return base_url + params


def _get_em_for_ticker(ticker: str) -> int:
    """
    Get Finam emitent ID for a given MOEX ticker.
    
    Args:
        ticker: MOEX ticker symbol
    
    Returns:
        Finam emitent ID
    
    Raises:
        ValueError: If ticker not found in configuration
    """
    for sector_id, sector_data in SECTORS.items():
        if sector_data.get("RU") == ticker:
            em = sector_data.get("RU_EM")
            if em is not None:
                return em
    raise ValueError(f"Finam emitent ID not found for ticker: {ticker}")


def fetch_finam_data(ticker: str, start_date: datetime, end_date: datetime) -> dict:
    """
    Fetch stock data from Finam Export API with robust error handling.
    
    Args:
        ticker: MOEX ticker symbol (e.g., 'SBER')
        start_date: Start date for data retrieval
        end_date: End date for data retrieval
    
    Returns:
        Dict with keys: df, success, actual_end_date, requested_end_date, date_adjusted, error
    """
    result = {
        'df': None,
        'success': False,
        'actual_end_date': None,
        'requested_end_date': end_date,
        'date_adjusted': False,
        'error': None
    }
    
    try:
        try:
            em = _get_em_for_ticker(ticker)
        except ValueError as e:
            logger.error("Ticker configuration error: %s", str(e))
            result['error'] = f"unknown: {str(e)}"
            return result
        
        timeout = API_CONFIG["finam"]["timeout_seconds"]
        max_retries = API_CONFIG["finam"]["max_retries"]
        retry_delay = API_CONFIG["finam"]["retry_delay_seconds"]
        
        response = None
        
        # Retry mechanism with custom exceptions
        for attempt in range(max_retries):
            try:
                url = _build_finam_url(ticker, em, start_date, end_date)
                response = requests.get(
                    url, 
                    timeout=timeout,
                    headers={'User-Agent': 'Mozilla/5.0 (compatible; EurasianBridge/1.0)'}
                )
                response.raise_for_status()
                break
            except requests.exceptions.Timeout as e:
                if attempt == max_retries - 1:
                    raise UpstreamTimeoutError(f"Finam API timed out after {max_retries} attempts", e)
                time.sleep(retry_delay)
            except requests.exceptions.ConnectionError as e:
                # requests.exceptions.ConnectionError includes DNS failures, refused connections, etc
                if attempt == max_retries - 1:
                    raise UpstreamConnectionError(f"Finam API connection failed", e)
                time.sleep(retry_delay)
            except requests.exceptions.HTTPError as e:
                # 4xx or 5xx errors - no point retrying usually, unless 503/502/504
                # For simplicity, we treat them as DataSourceErrors immediately
                raise DataSourceError(f"Finam API returned HTTP error", e, error_code=f"api_error: {str(e)}")

        if response is None or not response.text.strip():
            result['error'] = "no_data"
            return result
        
        # Parse CSV response
        try:
            df = pd.read_csv(
                io.StringIO(response.text),
                sep=',',
                parse_dates=False
            )
        except Exception as e:
            raise DataSourceError(f"Failed to parse Finam CSV response", e, error_code="api_error: Failed to parse response")
        
        # Finam CSV columns: <TICKER>,<PER>,<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOL>
        if '<CLOSE>' not in df.columns or '<DATE>' not in df.columns:
            # Check if API returned a text error masked as 200 OK (common in legacy financial APIs)
            logger.error("Unexpected Finam CSV format/content for %s: %s", ticker, str(response.text[:100]))
            result['error'] = "no_data"
            return result
        
        # Convert to standard format
        df['Date'] = pd.to_datetime(df['<DATE>'], format='%Y%m%d')
        df['Close'] = pd.to_numeric(df['<CLOSE>'], errors='coerce')
        df = df[['Date', 'Close']].dropna()
        df.set_index('Date', inplace=True)
        df.sort_index(inplace=True)
        
        min_points = DATA_CONFIG["min_data_points"]
        if len(df) < min_points:
            result['error'] = "insufficient_data"
            return result
        
        # Get actual end date from data
        actual_end = df.index.max()
        requested_end = pd.to_datetime(end_date)
        
        result['df'] = df
        result['success'] = True
        result['actual_end_date'] = actual_end
        result['date_adjusted'] = actual_end.date() < requested_end.date()
        
        return result

    except DataSourceError as e:
        logger.error(f"{type(e).__name__}: {str(e)}")
        result['error'] = e.error_code
        return result
    except Exception as e:
        logger.exception("Unexpected error fetching Finam data for %s", ticker)
        result['error'] = f"unknown: {str(e)}"
        return result


@st.cache_data(ttl=CACHE_CONFIG["ttl_seconds"])
def fetch_stock_data(ticker: str, start_date: datetime, end_date: datetime, is_russian: bool = False) -> dict:
    """
    Fetch stock data with robust error handling.
    
    Args:
        ticker: Stock ticker symbol
        start_date: Start date for data retrieval
        end_date: End date for data retrieval
        is_russian: If True, use Finam Export API; otherwise use Yahoo Finance
    
    Returns:
        Dict with keys: df, success, actual_end_date, requested_end_date, date_adjusted, error
    """
    if is_russian:
        return fetch_finam_data(ticker, start_date, end_date)
    
    result = {
        'df': None,
        'success': False,
        'actual_end_date': None,
        'requested_end_date': end_date,
        'date_adjusted': False,
        'error': None
    }
    
    # Use yfinance for Turkish stocks
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(start=start_date, end=end_date, auto_adjust=False)
        
        if df.empty:
            result['error'] = "no_data"
            return result
            
        min_points = DATA_CONFIG["min_data_points"]
        if len(df) < min_points:
            result['error'] = "insufficient_data"
            return result
        
        # Keep only Close price (unadjusted - real market prices)
        df = df[['Close']].copy()
        df.index = df.index.tz_localize(None)
        
        # Get actual end date from data
        actual_end = df.index.max()
        requested_end = pd.to_datetime(end_date)
        
        result['df'] = df
        result['success'] = True
        result['actual_end_date'] = actual_end
        result['date_adjusted'] = actual_end.date() < requested_end.date()
        
        return result
        
    except Exception as e:
        logger.exception("Unexpected error fetching Yahoo Finance data for %s", ticker)
        result['error'] = f"unknown: {str(e)}"
        return result



async def fetch_finam_data_async(ticker: str, start_date: datetime, end_date: datetime) -> dict:
    """
    Async fetch stock data from Finam Export API.
    Note: For caching stability, we prefer using the synchronous fetch_stock_data via to_thread.
    This implementation remains for reference or high-throughput scenarios where caching isn't priority.
    """
    # ... implementation (can keep as is or just wrap sync? Let's keep existing logic but remove cache)
    result = {
        'df': None,
        'success': False,
        'actual_end_date': None,
        'requested_end_date': end_date,
        'date_adjusted': False,
        'error': None
    }
    
    try:
        try:
            em = _get_em_for_ticker(ticker)
        except ValueError as e:
            logger.error("Ticker configuration error: %s", str(e))
            result['error'] = f"unknown: {str(e)}"
            return result
        
        timeout = API_CONFIG["finam"]["timeout_seconds"]
        max_retries = API_CONFIG["finam"]["max_retries"]
        retry_delay = API_CONFIG["finam"]["retry_delay_seconds"]
        
        response_text = None
        
        async with aiohttp.ClientSession() as session:
            for attempt in range(max_retries):
                try:
                    url = _build_finam_url(ticker, em, start_date, end_date)
                    headers = {'User-Agent': 'Mozilla/5.0 (compatible; EurasianBridge/1.0)'}
                    
                    async with session.get(url, timeout=timeout, headers=headers) as response:
                        if response.status >= 400:
                             response.raise_for_status()
                        
                        response_text = await response.text()
                        break
                except asyncio.TimeoutError as e:
                    if attempt == max_retries - 1:
                        logger.warning(f"Finam API async timeout for {ticker}")
                        result['error'] = "timeout"
                        return result
                    await asyncio.sleep(retry_delay)
                except aiohttp.ClientError as e:
                    if attempt == max_retries - 1:
                        logger.warning(f"Finam API async connection error for {ticker}: {str(e)}")
                        result['error'] = "connection"
                        return result
                    await asyncio.sleep(retry_delay)
                except Exception as e:
                     logger.warning(f"Finam API async error for {ticker}: {str(e)}")
                     if attempt == max_retries - 1:
                         result['error'] = f"api_error: {str(e)}"
                         return result
                     await asyncio.sleep(retry_delay)

        if not response_text or not response_text.strip():
            result['error'] = "no_data"
            return result
        
        # Parse CSV (synchronous using pandas)
        try:
            df = pd.read_csv(
                io.StringIO(response_text),
                sep=',',
                parse_dates=False
            )
        except Exception as e:
            logger.error("Failed to parse Finam CSV for %s: %s", ticker, str(e))
            result['error'] = "api_error: Failed to parse response"
            return result
        
        if '<CLOSE>' not in df.columns or '<DATE>' not in df.columns:
            logger.error("Unexpected Finam CSV format for %s", ticker)
            result['error'] = "no_data"
            return result
        
        # Convert to standard format
        df['Date'] = pd.to_datetime(df['<DATE>'], format='%Y%m%d')
        df['Close'] = pd.to_numeric(df['<CLOSE>'], errors='coerce')
        df = df[['Date', 'Close']].dropna()
        df.set_index('Date', inplace=True)
        df.sort_index(inplace=True)
        
        min_points = DATA_CONFIG["min_data_points"]
        if len(df) < min_points:
            result['error'] = "insufficient_data"
            return result
        
        actual_end = df.index.max()
        requested_end = pd.to_datetime(end_date)
        
        result['df'] = df
        result['success'] = True
        result['actual_end_date'] = actual_end
        result['date_adjusted'] = actual_end.date() < requested_end.date()
        
        return result

    except Exception as e:
        logger.exception("Unexpected error fetching Finam data async for %s", ticker)
        result['error'] = f"unknown: {str(e)}"
        return result


async def fetch_stock_data_async(ticker: str, start_date: datetime, end_date: datetime, is_russian: bool = False) -> dict:
    """
    Async fetch stock data.
    Uses cached synchronous fetch_stock_data via to_thread for BOTH sources to ensure caching works.
    """
    # Use thread pool to run synchronous, cached function
    # This prevents 'UnserializableReturnValueError' and ensures caching works for async calls
    return await asyncio.to_thread(fetch_stock_data, ticker, start_date, end_date, is_russian)


async def fetch_usd_rates_async(start_date: datetime, end_date: datetime) -> dict:
    """Async wrapper for fetch_usd_rates."""
    return await asyncio.to_thread(fetch_usd_rates, start_date, end_date)



async def fetch_ytd_start_price(ticker: str, is_russian: bool = False) -> Decimal:
    """
    Fetch the starting price of the year (first trading day in Jan).
    
    Args:
        ticker: Stock ticker
        is_russian: True if MOEX stock
    
    Returns:
        Start price as Decimal, or 0 if fails
    """
    try:
        now = datetime.now()
        start_year = datetime(now.year, 1, 1)
        # Fetch first 20 days of January to handle long holidays (RU)
        end_jan = datetime(now.year, 1, 20)
        
        # We need a separate fetch because main data might not go back to Jan 1st
        result = await fetch_stock_data_async(ticker, start_year, end_jan, is_russian)
        
        if not result['success'] or result['df'] is None or result['df'].empty:
            return Decimal("0.0")
            
        # Get first available price in the year
        start_price_raw = result['df'].iloc[0]['Close']
        return Decimal(str(start_price_raw))
        
    except Exception as e:
        logger.warning(f"Failed to fetch YTD start price for {ticker}: {e}")
        return Decimal("0.0")


async def fetch_market_cap_async(ticker: str, is_russian: bool = False) -> float:
    """
    Fetch Market Capitalization in Billions USD.
    Values come from the curated configuration snapshot for presentation consistency.
    
    Args:
        ticker: Stock ticker
        is_russian: True if MOEX stock
    
    Returns:
        Market Cap in Billions USD, or 0.0 if unavailable
    """
    cap = MARKET_CAPS.get(ticker)
    return float(cap) if cap is not None else 0.0
