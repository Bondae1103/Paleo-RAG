"""
Standard error hierarchy for PaleoRAG bioinformatics and database operations.
"""
from __future__ import annotations


class BioError(Exception):
    """Base exception for all biological processing and database errors."""
    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class SequenceValidationError(BioError):
    """Raised when a molecular sequence fails validation (e.g. invalid IUPAC characters)."""
    pass


class SequenceConversionError(BioError):
    """Raised when sequence format conversion (FASTA/GenBank/EMBL) fails."""
    pass


class DatabaseClientError(BioError):
    """Raised when an external biological database API fails."""
    def __init__(self, message: str, database: str, status_code: int | None = None, details: dict | None = None) -> None:
        super().__init__(message, details)
        self.database = database
        self.status_code = status_code


class DatabaseNotFoundError(DatabaseClientError):
    """Raised when a requested biological record is not found (HTTP 404)."""
    pass


class DatabaseRateLimitError(DatabaseClientError):
    """Raised when an external database enforces a rate limit (HTTP 429)."""
    pass


class DatabaseAuthError(DatabaseClientError):
    """Raised when an external database requires an API key that is missing or rejected."""
    pass
