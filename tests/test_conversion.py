
import pandas as pd
import pytest
from decimal import Decimal
from src.data import convert_to_usd

class TestConvertToUsd:
    def test_convert_to_usd_returns_decimal(self):
        """Verify that conversion returns Decimal objects."""
        # Setup data
        dates = pd.date_range('2024-01-01', periods=3)
        prices = pd.Series([100.0, 200.0, 300.0], index=dates, name='price')
        
        rates_df = pd.DataFrame({
            'USD_TRY': [10.0, 20.0, 30.0]
        }, index=dates)
        
        usd_rates = {'USD_TRY': rates_df}
        
        # Run conversion
        result = convert_to_usd(prices, 'TRY', usd_rates)
        
        # Verify
        assert len(result) == 3
        # Check first element is Decimal
        assert isinstance(result.iloc[0], Decimal), f"Expected Decimal, got {type(result.iloc[0])}"
        
        # Check values
        # 100/10 = 10
        assert result.iloc[0] == Decimal('10')
        assert result.iloc[1] == Decimal('10')
        assert result.iloc[2] == Decimal('10')

    def test_convert_to_usd_rub(self):
        """Verify RUB conversion works similarly."""
        dates = pd.date_range('2024-01-01', periods=2)
        prices = pd.Series([5000.0, 6000.0], index=dates, name='price')
        
        rates_df = pd.DataFrame({
            'USD_RUB': [100.0, 200.0] # 50, 30
        }, index=dates)
        
        usd_rates = {'USD_RUB': rates_df}
        
        result = convert_to_usd(prices, 'RUB', usd_rates)
        
        assert isinstance(result.iloc[0], Decimal)
        assert result.iloc[0] == Decimal('50')
        assert result.iloc[1] == Decimal('30')

    def test_forward_fills_missing_exchange_rates(self):
        """Missing FX observations inside the window should use the previous rate."""
        price_dates = pd.date_range('2024-01-01', periods=3)
        rate_dates = pd.to_datetime(['2024-01-01', '2024-01-03'])
        prices = pd.Series([100.0, 120.0, 150.0], index=price_dates, name='price')

        rates_df = pd.DataFrame({
            'USD_TRY': [10.0, 15.0]
        }, index=rate_dates)

        result = convert_to_usd(prices, 'TRY', {'USD_TRY': rates_df})

        assert len(result) == 3
        assert result.iloc[0] == Decimal('10')
        assert result.iloc[1] == Decimal('12')
        assert result.iloc[2] == Decimal('10')

    def test_handles_missing_rates(self):
        """Should return original series if rates missing."""
        dates = pd.date_range('2024-01-01', periods=1)
        prices = pd.Series([100.0], index=dates)
        usd_rates = {} # Empty
        
        result = convert_to_usd(prices, 'TRY', usd_rates)
        
        # Should return original (float)
        assert result.iloc[0] == 100.0
        assert isinstance(result.iloc[0], float) 
