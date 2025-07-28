from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Dict, Optional

from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.inspection import inspect


class ApiHelpers:
    @classmethod
    def _serialize_sqlalchemy_obj(cls, obj: Any) -> Dict[str, Any]:
        if not hasattr(obj, "__table__"):
            return obj

        result: Dict[str, Any] = {}
        mapper = inspect(obj.__class__)

        for column in mapper.columns:
            value = getattr(obj, column.name)
            result[column.name] = cls._serialize_value(value)

        for relationship in mapper.relationships:
            if hasattr(obj, relationship.key):
                related_obj = getattr(obj, relationship.key)
                if related_obj is not None:
                    if relationship.uselist:
                        result[relationship.key] = [
                            cls._serialize_sqlalchemy_obj(item) for item in related_obj
                        ]
                    else:
                        result[relationship.key] = cls._serialize_sqlalchemy_obj(
                            related_obj
                        )

        return result

    @classmethod
    def _serialize_pydantic_obj(cls, obj: BaseModel) -> Dict[str, Any]:
        return obj.model_dump()

    @classmethod
    def _serialize_value(cls, value: Any) -> Any:
        if value is None:
            return None
        elif isinstance(value, (str, int, float, bool)):
            return value
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, date):
            return value.isoformat()
        elif isinstance(value, time):
            return value.isoformat()
        elif isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, bytes):
            try:
                return value.decode("utf-8")
            except UnicodeDecodeError:
                return value.hex()
        elif hasattr(value, "__dict__") and hasattr(value, "__table__"):
            return cls._serialize_sqlalchemy_obj(value)
        elif isinstance(value, BaseModel):
            return cls._serialize_pydantic_obj(value)
        elif isinstance(value, (list, tuple)):
            return [cls._serialize_value(item) for item in value]
        elif isinstance(value, dict):
            return {key: cls._serialize_value(val) for key, val in value.items()}
        elif hasattr(value, "to_dict"):
            return value.to_dict()
        elif hasattr(value, "__dict__"):
            return {
                key: cls._serialize_value(val)
                for key, val in value.__dict__.items()
                if not key.startswith("_")
            }
        else:
            try:
                return str(value)
            except Exception:
                return f"<{type(value).__name__} object>"

    @classmethod
    def _serialize_data(cls, data: Any) -> Any:
        if data is None:
            return None
        elif isinstance(data, (list, tuple)):
            return [cls._serialize_value(item) for item in data]
        else:
            return cls._serialize_value(data)

    @classmethod
    def endpointResponse(
        cls,
        status_code: int,
        message: str,
        data: Optional[Any] = None,
        **kwargs: Any,
    ) -> JSONResponse:
        serialized_data = cls._serialize_data(data)

        response: Dict[str, Any] = {
            "status_code": status_code,
            "message": message,
            "data": serialized_data,
        }

        for key, value in kwargs.items():
            response[key] = cls._serialize_value(value)

        return JSONResponse(status_code=status_code, content=response)

    @classmethod
    def endpointError(
        cls,
        status_code: int,
        message: str,
        errors: Optional[Any] = None,
        **kwargs: Any,
    ) -> JSONResponse:
        serialized_errors = cls._serialize_data(errors)

        response: Dict[str, Any] = {
            "status_code": status_code,
            "message": message,
            "success": False,
        }

        if errors is not None:
            response["errors"] = serialized_errors

        for key, value in kwargs.items():
            response[key] = cls._serialize_value(value)

        return JSONResponse(status_code=status_code, content=response)
