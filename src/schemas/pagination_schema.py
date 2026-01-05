"""
Pagination request and response schemas for KU-RUN Check-in Backend.

This module defines Pydantic schemas for handling pagination in API requests
and responses, providing consistent structure for paginated data across the application.
"""

from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """
    Pagination parameters for request queries.
    
    Attributes:
        page: The page number (1-indexed). Defaults to 1.
        page_size: The number of items per page. Defaults to 10.
        limit: Alternative parameter name for page_size. If provided, takes precedence.
        offset: Alternative pagination parameter (number of items to skip).
    """

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=10, ge=1, le=100, description="Number of items per page")
    limit: Optional[int] = Field(default=None, ge=1, le=100, description="Alternative to page_size")
    offset: Optional[int] = Field(default=None, ge=0, description="Number of items to skip")

    def get_limit(self) -> int:
        """Get the effective limit/page_size."""
        return self.limit or self.page_size

    def get_offset(self) -> int:
        """Get the effective offset based on page and page_size."""
        if self.offset is not None:
            return self.offset
        return (self.page - 1) * self.get_limit()


class PaginationMeta(BaseModel):
    """
    Pagination metadata for response.
    
    Attributes:
        current_page: The current page number.
        page_size: The number of items per page.
        total_items: The total number of items available.
        total_pages: The total number of pages.
        has_next: Whether there is a next page.
        has_previous: Whether there is a previous page.
    """

    current_page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of items per page")
    total_items: int = Field(description="Total number of items available")
    total_pages: int = Field(description="Total number of pages")
    has_next: bool = Field(description="Whether there is a next page")
    has_previous: bool = Field(description="Whether there is a previous page")

    @staticmethod
    def from_pagination(
        page: int, page_size: int, total_items: int
    ) -> "PaginationMeta":
        """
        Create PaginationMeta from pagination parameters.
        
        Args:
            page: Current page number (1-indexed).
            page_size: Number of items per page.
            total_items: Total number of items.
            
        Returns:
            PaginationMeta instance with calculated values.
        """
        total_pages = (total_items + page_size - 1) // page_size
        return PaginationMeta(
            current_page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response schema.
    
    Attributes:
        data: List of items in the current page.
        pagination: Pagination metadata.
        message: Optional success message.
    """

    data: List[T] = Field(description="List of items in the current page")
    pagination: PaginationMeta = Field(description="Pagination metadata")
    message: Optional[str] = Field(
        default="Success", description="Response message"
    )

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "data": [],
                "pagination": {
                    "current_page": 1,
                    "page_size": 10,
                    "total_items": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_previous": False,
                },
                "message": "Success",
            }
        }


class SimplePaginationParams(BaseModel):
    """
    Simplified pagination parameters.
    
    Attributes:
        limit: Maximum number of items to return.
        offset: Number of items to skip.
    """

    limit: int = Field(default=10, ge=1, le=100, description="Maximum items to return")
    offset: int = Field(default=0, ge=0, description="Number of items to skip")


class OffsetPaginatedResponse(BaseModel, Generic[T]):
    """
    Offset-based paginated response schema.
    
    Attributes:
        data: List of items.
        limit: Maximum items returned.
        offset: Number of items skipped.
        total: Total number of items available.
    """

    data: List[T] = Field(description="List of items")
    limit: int = Field(description="Maximum items returned")
    offset: int = Field(description="Number of items skipped")
    total: int = Field(description="Total number of items available")

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "data": [],
                "limit": 10,
                "offset": 0,
                "total": 0,
            }
        }
