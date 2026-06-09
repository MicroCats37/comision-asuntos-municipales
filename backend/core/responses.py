from typing import Any, Optional, Generic, TypeVar
from pydantic import Field
from ninja import Schema

T = TypeVar("T")

class ErrorDetail(Schema):
    """Standardized error detail."""

    code: str = Field(..., description="Unique machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict] = Field(None, description="Optional extra details about the error")


class ApiResponse(Schema, Generic[T]):
    """Standard API response envelope."""

    success: bool = Field(..., description="Indicates if the API request was successful")
    data: Optional[T] = Field(None, description="The payload of the response")
    error: Optional[ErrorDetail] = Field(None, description="Error details if the request failed")


class PaginationMeta(Schema):
    """Pagination metadata."""

    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")


class PaginatedApiResponse(Schema, Generic[T]):
    """Paginated API response envelope."""

    success: bool = Field(..., description="Indicates if the API request was successful")
    data: Optional[list[T]] = Field(None, description="The list of items in the current page")
    error: Optional[ErrorDetail] = Field(None, description="Error details if the request failed")
    meta: Optional[PaginationMeta] = Field(None, description="Pagination metadata")


def success_response(data: Any = None) -> dict:
    """Wrap data in a standard success envelope."""
    return {"success": True, "data": data, "error": None}


def error_response(
    code: str,
    message: str,
    details: dict | None = None,
    status: int = 400,
) -> tuple[dict, int]:
    """Return a standard error envelope with HTTP status code."""
    body = {
        "success": False,
        "data": None,
        "error": {"code": code, "message": message, "details": details},
    }
    return body, status
