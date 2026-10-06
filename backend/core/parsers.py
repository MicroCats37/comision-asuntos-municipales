from typing import Type, TypeVar
from ninja import Schema
from .types import parse_form_json

T = TypeVar("T", bound=Schema)

# Re-export para backward compatibility
__all__ = ["parse_form_json"]
