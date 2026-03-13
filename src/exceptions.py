"""
Custom exceptions for The Eurasian Bridge application.
Provides a structured hierarchy for error handling.
"""

class BistMoexError(Exception):
    """Base exception for the application."""
    pass

class DataSourceError(BistMoexError):
    """Raised when fetching data from external APIs fails."""
    def __init__(self, message: str, original_exception: Exception = None, error_code: str = "unknown"):
        super().__init__(message)
        self.original_exception = original_exception
        self.error_code = error_code

class UpstreamTimeoutError(DataSourceError):
    """Raised when an upstream API times out."""
    def __init__(self, message: str = "Upstream service timeout", original_exception: Exception = None):
        super().__init__(message, original_exception, error_code="timeout")

class UpstreamConnectionError(DataSourceError):
    """Raised when connection to upstream API fails."""
    def __init__(self, message: str = "Upstream connection failed", original_exception: Exception = None):
        super().__init__(message, original_exception, error_code="connection")

class ValidationError(BistMoexError):
    """Raised when input validation fails."""
    pass
