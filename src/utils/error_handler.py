"""
Standardized error response handling module.

This module provides utilities for creating consistent error responses
across the application, including custom exception classes and error
response formatting.
"""

from typing import Any, Dict, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """Standard error codes for the application."""
    
    # Client errors (4xx)
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNPROCESSABLE_ENTITY = "UNPROCESSABLE_ENTITY"
    
    # Server errors (5xx)
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    
    # Application-specific errors
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    PERMISSION_ERROR = "PERMISSION_ERROR"


class HTTPStatusCode(Enum):
    """HTTP status codes."""
    
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503
    NOT_IMPLEMENTED = 501


class ApplicationException(Exception):
    """Base exception class for application-specific errors."""
    
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        status_code: HTTPStatusCode = HTTPStatusCode.INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize ApplicationException.
        
        Args:
            error_code: Standard error code from ErrorCode enum
            message: Human-readable error message
            status_code: HTTP status code (defaults to 500)
            details: Additional error details as a dictionary
            cause: Original exception that caused this error
        """
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.cause = cause
        
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary representation."""
        return {
            "error_code": self.error_code.value,
            "message": self.message,
            "status_code": self.status_code.value,
            "details": self.details,
        }


class BadRequestError(ApplicationException):
    """Exception for bad request (400) errors."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            error_code=ErrorCode.BAD_REQUEST,
            message=message,
            status_code=HTTPStatusCode.BAD_REQUEST,
            details=details,
            cause=cause,
        )


class UnauthorizedError(ApplicationException):
    """Exception for unauthorized (401) errors."""
    
    def __init__(
        self,
        message: str = "Unauthorized",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            error_code=ErrorCode.UNAUTHORIZED,
            message=message,
            status_code=HTTPStatusCode.UNAUTHORIZED,
            details=details,
            cause=cause,
        )


class ForbiddenError(ApplicationException):
    """Exception for forbidden (403) errors."""
    
    def __init__(
        self,
        message: str = "Forbidden",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            error_code=ErrorCode.FORBIDDEN,
            message=message,
            status_code=HTTPStatusCode.FORBIDDEN,
            details=details,
            cause=cause,
        )


class NotFoundError(ApplicationException):
    """Exception for not found (404) errors."""
    
    def __init__(
        self,
        message: str = "Resource not found",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            error_code=ErrorCode.NOT_FOUND,
            message=message,
            status_code=HTTPStatusCode.NOT_FOUND,
            details=details,
            cause=cause,
        )


class ConflictError(ApplicationException):
    """Exception for conflict (409) errors."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            error_code=ErrorCode.CONFLICT,
            message=message,
            status_code=HTTPStatusCode.CONFLICT,
            details=details,
            cause=cause,
        )


class ValidationError(ApplicationException):
    """Exception for validation errors."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            error_code=ErrorCode.VALIDATION_ERROR,
            message=message,
            status_code=HTTPStatusCode.UNPROCESSABLE_ENTITY,
            details=details,
            cause=cause,
        )


class DatabaseError(ApplicationException):
    """Exception for database-related errors."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            error_code=ErrorCode.DATABASE_ERROR,
            message=message,
            status_code=HTTPStatusCode.INTERNAL_SERVER_ERROR,
            details=details,
            cause=cause,
        )


class ExternalServiceError(ApplicationException):
    """Exception for external service-related errors."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message=message,
            status_code=HTTPStatusCode.SERVICE_UNAVAILABLE,
            details=details,
            cause=cause,
        )


class ErrorResponse:
    """Standardized error response formatter."""
    
    @staticmethod
    def format_error(
        error_code: ErrorCode,
        message: str,
        status_code: HTTPStatusCode,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Format a standardized error response.
        
        Args:
            error_code: Standard error code
            message: Error message
            status_code: HTTP status code
            details: Additional error details
            request_id: Optional request ID for tracking
            
        Returns:
            Dictionary with standardized error response format
        """
        response = {
            "success": False,
            "error": {
                "code": error_code.value,
                "message": message,
                "status": status_code.value,
            },
        }
        
        if details:
            response["error"]["details"] = details
        
        if request_id:
            response["request_id"] = request_id
        
        return response
    
    @staticmethod
    def format_exception(
        exception: ApplicationException,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Format an ApplicationException as an error response.
        
        Args:
            exception: ApplicationException instance
            request_id: Optional request ID for tracking
            
        Returns:
            Dictionary with standardized error response format
        """
        return ErrorResponse.format_error(
            error_code=exception.error_code,
            message=exception.message,
            status_code=exception.status_code,
            details=exception.details if exception.details else None,
            request_id=request_id,
        )
    
    @staticmethod
    def format_generic_error(
        message: str = "An unexpected error occurred",
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Format a generic error response for unhandled exceptions.
        
        Args:
            message: Error message
            request_id: Optional request ID for tracking
            
        Returns:
            Dictionary with standardized error response format
        """
        return ErrorResponse.format_error(
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            message=message,
            status_code=HTTPStatusCode.INTERNAL_SERVER_ERROR,
            request_id=request_id,
        )


class ErrorHandler:
    """Utility class for handling and logging errors."""
    
    @staticmethod
    def handle_exception(
        exception: Exception,
        logger_instance: Optional[logging.Logger] = None,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Handle an exception and return a formatted error response.
        
        Args:
            exception: Exception to handle
            logger_instance: Logger instance for logging the error
            request_id: Optional request ID for tracking
            
        Returns:
            Formatted error response dictionary
        """
        log_func = logger_instance.error if logger_instance else logger.error
        
        if isinstance(exception, ApplicationException):
            log_func(
                f"Application error [{exception.error_code.value}]: {exception.message}",
                extra={"request_id": request_id, "details": exception.details},
            )
            return ErrorResponse.format_exception(exception, request_id)
        else:
            log_func(
                f"Unexpected error: {str(exception)}",
                exc_info=True,
                extra={"request_id": request_id},
            )
            return ErrorResponse.format_generic_error(request_id=request_id)
    
    @staticmethod
    def log_error(
        error_code: ErrorCode,
        message: str,
        logger_instance: Optional[logging.Logger] = None,
        **kwargs,
    ) -> None:
        """
        Log an error with context information.
        
        Args:
            error_code: Error code
            message: Error message
            logger_instance: Logger instance
            **kwargs: Additional context information
        """
        log_func = logger_instance.error if logger_instance else logger.error
        log_func(f"[{error_code.value}] {message}", extra=kwargs)
