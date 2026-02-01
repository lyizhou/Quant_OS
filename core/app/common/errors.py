"""Custom exception classes for the application."""

from __future__ import annotations


class QuantOSError(Exception):
    """Base exception for all Quant_OS errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


# Configuration Errors
class ConfigurationError(QuantOSError):
    """Raised when configuration is invalid or missing."""

    pass


# Data Errors
class DataFetchError(QuantOSError):
    """Raised when data fetching fails."""

    pass


class DataValidationError(QuantOSError):
    """Raised when data validation fails."""

    pass


# Database Errors
class DatabaseError(QuantOSError):
    """Raised when database operations fail."""

    pass


class RecordNotFoundError(DatabaseError):
    """Raised when a database record is not found."""

    pass


# Driver Errors
class DriverError(QuantOSError):
    """Base exception for driver-related errors."""

    pass


class USMarketDriverError(DriverError):
    """Raised when US market driver encounters an error."""

    pass


class CNMarketDriverError(DriverError):
    """Raised when CN market driver encounters an error."""

    pass


class InfoDriverError(DriverError):
    """Raised when info driver encounters an error."""

    pass


# Kernel Errors
class KernelError(QuantOSError):
    """Base exception for kernel-related errors."""

    pass


class MappingCoreError(KernelError):
    """Raised when mapping core encounters an error."""

    pass


class NarrativeCoreError(KernelError):
    """Raised when narrative core encounters an error."""

    pass


class RiskCoreError(KernelError):
    """Raised when risk core encounters an error."""

    pass


# External Service Errors
class ExternalServiceError(QuantOSError):
    """Raised when external service calls fail."""

    pass


class TelegramError(ExternalServiceError):
    """Raised when Telegram API calls fail."""

    pass


class AIServiceError(ExternalServiceError):
    """Raised when AI service (DeepSeek, etc.) calls fail."""

    pass


# Use Case Errors
class UseCaseError(QuantOSError):
    """Base exception for use case execution errors."""

    pass
