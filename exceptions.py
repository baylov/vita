"""Custom exceptions for the application."""


class ApplicationError(Exception):
    """Base exception for the application."""

    pass


class RecoverableExternalError(ApplicationError):
    """Raised when an external API call fails after retries are exhausted."""

    def __init__(self, message: str, service_name: str = "Unknown"):
        self.message = message
        self.service_name = service_name
        super().__init__(f"{service_name}: {message}")


class SheetsError(ApplicationError):
    """Raised when a Google Sheets operation fails."""

    pass


class SheetsInitializationError(SheetsError):
    """Raised when Sheets manager initialization fails."""

    pass


class SyncError(ApplicationError):
    """Raised when a sync operation fails."""

    pass


class ConflictError(ApplicationError):
    """Raised when a conflict is detected during sync."""

    pass
