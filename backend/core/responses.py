from decimal import Decimal
from typing import Any, Optional, Generic, TypeVar
from pydantic import Field, BaseModel
from ninja import Schema

T = TypeVar("T")


def _decimal_to_float(obj: Any) -> Any:
    """Recursively convert all Decimal values to float in a nested structure.

    Ensures JSON serialization produces numeric values (not strings) for Decimal fields.
    """
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_decimal_to_float(item) for item in obj]
    if isinstance(obj, BaseModel):
        # Serialize via model_dump then convert (model_dump returns plain dict with Decimals intact)
        return _decimal_to_float(obj.model_dump())
    return obj


class ErrorDetail(Schema):
    """Standardized error detail."""

    code: str = Field(..., description="Unique machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict] = Field(None, description="Optional extra details about the request failure")


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
    """Wrap data in a standard success envelope.

    Pydantic models are serialized via model_dump(mode='json'), which applies
    ser_json_decimal_to_float config to convert Decimals to JSON floats.
    Nested schemas are also serialized via model_dump(mode='json') to ensure
    consistent numeric output throughout the response tree.
    """
    if isinstance(data, BaseModel):
        # mode='json' applies ser_json_decimal_to_float and serializes nested schemas
        data = data.model_dump(mode='json')
    # _decimal_to_float as belt-and-suspenders for any remaining Decimals
    # (e.g., if mode='json' didn't fully recurse for some reason)
    data = _decimal_to_float(data)
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
