"""
Constants and Enums for KU-RUN Check-in Backend Application

This module contains all application-wide constants, enums, and configuration values
used throughout the KU-RUN Check-in backend system.
"""

from enum import Enum
from typing import Final

# ============================================================================
# API Response Constants
# ============================================================================

class HTTPStatusCodes:
    """HTTP status code constants"""
    OK: Final[int] = 200
    CREATED: Final[int] = 201
    ACCEPTED: Final[int] = 202
    NO_CONTENT: Final[int] = 204
    BAD_REQUEST: Final[int] = 400
    UNAUTHORIZED: Final[int] = 401
    FORBIDDEN: Final[int] = 403
    NOT_FOUND: Final[int] = 404
    CONFLICT: Final[int] = 409
    INTERNAL_SERVER_ERROR: Final[int] = 500
    SERVICE_UNAVAILABLE: Final[int] = 503


# ============================================================================
# Authentication & Authorization Constants
# ============================================================================

class AuthConstants:
    """Authentication and authorization related constants"""
    TOKEN_EXPIRY_MINUTES: Final[int] = 60
    REFRESH_TOKEN_EXPIRY_DAYS: Final[int] = 7
    PASSWORD_MIN_LENGTH: Final[int] = 8
    PASSWORD_MAX_LENGTH: Final[int] = 128
    TOKEN_PREFIX: Final[str] = "Bearer "
    SESSION_TIMEOUT_MINUTES: Final[int] = 30


class UserRole(str, Enum):
    """User role enumeration"""
    ADMIN = "admin"
    ORGANIZER = "organizer"
    VOLUNTEER = "volunteer"
    PARTICIPANT = "participant"
    GUEST = "guest"


class Permission(str, Enum):
    """Permission enumeration"""
    CREATE_EVENT = "create_event"
    EDIT_EVENT = "edit_event"
    DELETE_EVENT = "delete_event"
    VIEW_PARTICIPANTS = "view_participants"
    MANAGE_CHECKIN = "manage_checkin"
    VIEW_REPORTS = "view_reports"
    MANAGE_USERS = "manage_users"
    VIEW_ANALYTICS = "view_analytics"


# ============================================================================
# Event & Check-in Constants
# ============================================================================

class EventStatus(str, Enum):
    """Event status enumeration"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    POSTPONED = "postponed"


class CheckinStatus(str, Enum):
    """Check-in status enumeration"""
    PENDING = "pending"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    NO_SHOW = "no_show"
    EXCUSED_ABSENCE = "excused_absence"


class EventType(str, Enum):
    """Event type enumeration"""
    RACE = "race"
    TRAINING = "training"
    WORKSHOP = "workshop"
    MEETING = "meeting"
    SOCIAL = "social"
    COMPETITION = "competition"


class EventConstants:
    """Event-related constants"""
    EVENT_NAME_MAX_LENGTH: Final[int] = 200
    EVENT_DESCRIPTION_MAX_LENGTH: Final[int] = 2000
    MAX_PARTICIPANTS_UNLIMITED: Final[int] = -1
    MIN_PARTICIPANTS: Final[int] = 1
    MAX_LOCATION_LENGTH: Final[int] = 256


# ============================================================================
# Participant & Registration Constants
# ============================================================================

class RegistrationStatus(str, Enum):
    """Registration status enumeration"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    WAITLISTED = "waitlisted"
    REGISTERED = "registered"


class ParticipantStatus(str, Enum):
    """Participant status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BANNED = "banned"


class ParticipantConstants:
    """Participant-related constants"""
    NAME_MAX_LENGTH: Final[int] = 128
    EMAIL_MAX_LENGTH: Final[int] = 256
    PHONE_MAX_LENGTH: Final[int] = 20
    STUDENT_ID_MAX_LENGTH: Final[int] = 50


# ============================================================================
# Notification Constants
# ============================================================================

class NotificationType(str, Enum):
    """Notification type enumeration"""
    EVENT_REMINDER = "event_reminder"
    REGISTRATION_CONFIRMED = "registration_confirmed"
    CHECK_IN_CONFIRMATION = "check_in_confirmation"
    EVENT_UPDATE = "event_update"
    NEW_EVENT_PUBLISHED = "new_event_published"
    GENERAL_ANNOUNCEMENT = "general_announcement"


class NotificationChannel(str, Enum):
    """Notification channel enumeration"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationStatus(str, Enum):
    """Notification status enumeration"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERY_FAILED = "delivery_failed"
    READ = "read"


class NotificationConstants:
    """Notification-related constants"""
    EMAIL_SUBJECT_MAX_LENGTH: Final[int] = 256
    EMAIL_BODY_MAX_LENGTH: Final[int] = 5000
    NOTIFICATION_RETENTION_DAYS: Final[int] = 90
    REMINDER_HOURS_BEFORE_EVENT: Final[list] = [24, 1]  # Send reminders 24h and 1h before


# ============================================================================
# Report & Analytics Constants
# ============================================================================

class ReportType(str, Enum):
    """Report type enumeration"""
    ATTENDANCE = "attendance"
    REGISTRATION = "registration"
    PERFORMANCE = "performance"
    DEMOGRAPHICS = "demographics"
    ENGAGEMENT = "engagement"


class ReportFormat(str, Enum):
    """Report format enumeration"""
    PDF = "pdf"
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"


class ReportConstants:
    """Report-related constants"""
    MAX_REPORT_RECORDS: Final[int] = 100000
    REPORT_EXPIRY_DAYS: Final[int] = 30


# ============================================================================
# Validation Constants
# ============================================================================

class ValidationConstants:
    """Validation-related constants"""
    EMAIL_REGEX: Final[str] = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    PHONE_REGEX: Final[str] = r"^[\d\s\-\+\(\)]{7,20}$"
    USERNAME_MIN_LENGTH: Final[int] = 3
    USERNAME_MAX_LENGTH: Final[int] = 50
    USERNAME_REGEX: Final[str] = r"^[a-zA-Z0-9_-]+$"
    PASSWORD_REGEX: Final[str] = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"


# ============================================================================
# Pagination & Filtering Constants
# ============================================================================

class PaginationConstants:
    """Pagination-related constants"""
    DEFAULT_PAGE_SIZE: Final[int] = 20
    MAX_PAGE_SIZE: Final[int] = 100
    MIN_PAGE_SIZE: Final[int] = 1
    DEFAULT_PAGE_NUMBER: Final[int] = 1


class SortOrder(str, Enum):
    """Sort order enumeration"""
    ASC = "asc"
    DESC = "desc"


# ============================================================================
# Time & Date Constants
# ============================================================================

class TimeConstants:
    """Time and date related constants"""
    DATE_FORMAT: Final[str] = "%Y-%m-%d"
    DATETIME_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
    ISO_DATETIME_FORMAT: Final[str] = "%Y-%m-%dT%H:%M:%SZ"
    TIME_FORMAT: Final[str] = "%H:%M:%S"
    TIMEZONE_DEFAULT: Final[str] = "UTC"


# ============================================================================
# File Upload Constants
# ============================================================================

class FileConstants:
    """File upload and storage related constants"""
    MAX_FILE_SIZE_MB: Final[int] = 10
    MAX_FILE_SIZE_BYTES: Final[int] = 10 * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS: Final[list] = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    ALLOWED_DOCUMENT_EXTENSIONS: Final[list] = [".pdf", ".doc", ".docx", ".xlsx", ".csv"]
    UPLOAD_DIRECTORY: Final[str] = "uploads/"
    TEMP_UPLOAD_DIRECTORY: Final[str] = "temp_uploads/"


# ============================================================================
# Cache Constants
# ============================================================================

class CacheConstants:
    """Cache-related constants"""
    CACHE_TTL_MINUTES: Final[int] = 15
    CACHE_TTL_HOURS: Final[int] = 1
    CACHE_TTL_DAYS: Final[int] = 7
    CACHE_KEY_PREFIX: Final[str] = "ku_run:"
    EVENT_CACHE_KEY: Final[str] = f"{CACHE_KEY_PREFIX}event:"
    PARTICIPANT_CACHE_KEY: Final[str] = f"{CACHE_KEY_PREFIX}participant:"


# ============================================================================
# Error Messages
# ============================================================================

class ErrorMessages:
    """Application error messages"""
    INVALID_CREDENTIALS = "Invalid username or password"
    TOKEN_EXPIRED = "Token has expired"
    TOKEN_INVALID = "Invalid token"
    UNAUTHORIZED_ACCESS = "Unauthorized access"
    RESOURCE_NOT_FOUND = "Resource not found"
    RESOURCE_ALREADY_EXISTS = "Resource already exists"
    INVALID_INPUT = "Invalid input provided"
    SERVER_ERROR = "Internal server error"
    SERVICE_UNAVAILABLE = "Service is temporarily unavailable"
    EMAIL_ALREADY_EXISTS = "Email already registered"
    USERNAME_ALREADY_EXISTS = "Username already taken"
    EVENT_NOT_FOUND = "Event not found"
    PARTICIPANT_NOT_FOUND = "Participant not found"
    INVALID_EVENT_STATUS = "Invalid event status"
    REGISTRATION_CLOSED = "Registration for this event is closed"
    EVENT_FULL = "Event is at full capacity"
    DUPLICATE_CHECKIN = "Participant already checked in for this event"


# ============================================================================
# Success Messages
# ============================================================================

class SuccessMessages:
    """Application success messages"""
    CREATED_SUCCESSFULLY = "Created successfully"
    UPDATED_SUCCESSFULLY = "Updated successfully"
    DELETED_SUCCESSFULLY = "Deleted successfully"
    REGISTERED_SUCCESSFULLY = "Registered successfully"
    CHECKED_IN_SUCCESSFULLY = "Checked in successfully"
    LOGIN_SUCCESSFUL = "Login successful"
    LOGOUT_SUCCESSFUL = "Logout successful"
    PASSWORD_CHANGED = "Password changed successfully"
    EMAIL_VERIFIED = "Email verified successfully"


# ============================================================================
# Application Configuration Constants
# ============================================================================

class AppConfig:
    """Application configuration constants"""
    APP_NAME: Final[str] = "KU-RUN Check-in Backend"
    APP_VERSION: Final[str] = "1.0.0"
    DEBUG_MODE: Final[bool] = False
    LOG_LEVEL: Final[str] = "INFO"
    ENVIRONMENT: Final[str] = "production"
