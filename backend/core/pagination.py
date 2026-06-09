"""
Generic paginated data schemas for API responses.

Provides a reusable PaginatedData[T] schema that can be nested inside
ApiResponse for consistent paginated list endpoints.
"""
from typing import Generic, TypeVar
from ninja import Schema

T = TypeVar("T")


class PaginatedData(Schema, Generic[T]):
    """
    Generic paginated data container.

    Used inside ApiResponse[T] for list endpoints with pagination:
        ApiResponse[PaginatedData[PersonaListItem]]

    Response shape:
        {
            "success": true,
            "data": {
                "items": [...],
                "total": 5,
                "page": 1,
                "page_size": 10,
                "total_pages": 1
            },
            "error": null
        }
    """
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int