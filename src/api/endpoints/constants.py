"""
FastAPI router for constants and enums endpoints.

This module provides endpoints to retrieve application constants,
enums, and static data used throughout the API.

Created: 2026-01-05 03:55:16 UTC
Author: bell77m
"""

from enum import Enum
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status

router = APIRouter(
    prefix="/api/constants",
    tags=["constants"],
    responses={404: {"description": "Not found"}},
)


# Define enums for the application
class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "admin"
    ORGANIZER = "organizer"
    VOLUNTEER = "volunteer"
    PARTICIPANT = "participant"


class EventStatus(str, Enum):
    """Event status enumeration."""
    DRAFT = "draft"
    UPCOMING = "upcoming"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CheckInStatus(str, Enum):
    """Check-in status enumeration."""
    NOT_CHECKED_IN = "not_checked_in"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"


class NotificationType(str, Enum):
    """Notification type enumeration."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


# Constants
CONSTANTS = {
    "app_name": "KU RUN Check-in System",
    "app_version": "1.0.0",
    "api_version": "v1",
    "max_participants_per_event": 1000,
    "max_file_upload_size_mb": 10,
    "session_timeout_minutes": 30,
    "password_min_length": 8,
    "password_require_special_chars": True,
    "email_verification_required": True,
    "timezone": "UTC",
}


@router.get("/all", response_model=Dict[str, Any])
async def get_all_constants() -> Dict[str, Any]:
    """
    Retrieve all application constants and enums.

    Returns:
        Dict containing all constants and enums including:
        - app_metadata: Application name, version, and API version
        - config: Application configuration constants
        - enums: All available enumerations

    Example:
        GET /api/constants/all
        Response:
        {
            "app_metadata": {...},
            "config": {...},
            "enums": {...}
        }
    """
    return {
        "app_metadata": {
            "app_name": CONSTANTS["app_name"],
            "app_version": CONSTANTS["app_version"],
            "api_version": CONSTANTS["api_version"],
        },
        "config": CONSTANTS,
        "enums": {
            "user_roles": [role.value for role in UserRole],
            "event_statuses": [status.value for status in EventStatus],
            "check_in_statuses": [status.value for status in CheckInStatus],
            "notification_types": [notif.value for notif in NotificationType],
        },
    }


@router.get("/enums", response_model=Dict[str, Any])
async def get_enums() -> Dict[str, Any]:
    """
    Retrieve all available enumerations.

    Returns:
        Dict mapping enum types to their possible values:
        - user_roles: Available user roles in the system
        - event_statuses: Possible event status values
        - check_in_statuses: Possible check-in status values
        - notification_types: Available notification types

    Example:
        GET /api/constants/enums
        Response:
        {
            "user_roles": ["admin", "organizer", "volunteer", "participant"],
            "event_statuses": ["draft", "upcoming", "active", "completed", "cancelled"],
            "check_in_statuses": ["not_checked_in", "checked_in", "checked_out"],
            "notification_types": ["email", "sms", "push", "in_app"]
        }
    """
    return {
        "user_roles": [role.value for role in UserRole],
        "event_statuses": [status.value for status in EventStatus],
        "check_in_statuses": [status.value for status in CheckInStatus],
        "notification_types": [notif.value for notif in NotificationType],
    }


@router.get("/config", response_model=Dict[str, Any])
async def get_config() -> Dict[str, Any]:
    """
    Retrieve application configuration constants.

    Returns:
        Dict containing application-wide configuration settings

    Example:
        GET /api/constants/config
        Response:
        {
            "app_name": "KU RUN Check-in System",
            "app_version": "1.0.0",
            "max_participants_per_event": 1000,
            ...
        }
    """
    return CONSTANTS


@router.get("/user-roles", response_model=Dict[str, list])
async def get_user_roles() -> Dict[str, list]:
    """
    Retrieve available user roles.

    Returns:
        Dict containing list of available user roles

    Example:
        GET /api/constants/user-roles
        Response:
        {
            "roles": ["admin", "organizer", "volunteer", "participant"]
        }
    """
    return {"roles": [role.value for role in UserRole]}


@router.get("/event-statuses", response_model=Dict[str, list])
async def get_event_statuses() -> Dict[str, list]:
    """
    Retrieve available event statuses.

    Returns:
        Dict containing list of available event status values

    Example:
        GET /api/constants/event-statuses
        Response:
        {
            "statuses": ["draft", "upcoming", "active", "completed", "cancelled"]
        }
    """
    return {"statuses": [status.value for status in EventStatus]}


@router.get("/check-in-statuses", response_model=Dict[str, list])
async def get_check_in_statuses() -> Dict[str, list]:
    """
    Retrieve available check-in statuses.

    Returns:
        Dict containing list of available check-in status values

    Example:
        GET /api/constants/check-in-statuses
        Response:
        {
            "statuses": ["not_checked_in", "checked_in", "checked_out"]
        }
    """
    return {"statuses": [status.value for status in CheckInStatus]}


@router.get("/notification-types", response_model=Dict[str, list])
async def get_notification_types() -> Dict[str, list]:
    """
    Retrieve available notification types.

    Returns:
        Dict containing list of available notification types

    Example:
        GET /api/constants/notification-types
        Response:
        {
            "types": ["email", "sms", "push", "in_app"]
        }
    """
    return {"types": [notif.value for notif in NotificationType]}
