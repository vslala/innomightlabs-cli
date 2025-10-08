import inspect
from datetime import datetime, timezone
from typing import Annotated, Any, List, Literal, Union, get_args, get_origin, get_type_hints

from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo

from common.models import BaseTool

NoneType = type(None)

def Tool(func: Any) -> BaseTool:
    """Decorator to define a tool."""

    def unwrap_annotation(annotation: Any) -> tuple[Any, FieldInfo | None]:
        """Return the core annotation and any attached Field metadata."""
        field_info: FieldInfo | None = None
        while get_origin(annotation) is Annotated:
            args = get_args(annotation)
            annotation = args[0]
            for meta in args[1:]:
                if isinstance(meta, FieldInfo):
                    field_info = meta
        return annotation, field_info

    def is_optional(annotation: Any) -> bool:
        base_annotation, _ = unwrap_annotation(annotation)
        origin = get_origin(base_annotation)
        if origin is Union:
            return any(arg is NoneType for arg in get_args(base_annotation))
        return False

    def annotation_to_schema(annotation: Any) -> dict[str, Any]:
        base_annotation, field_info = unwrap_annotation(annotation)
        origin = get_origin(base_annotation)

        if origin is None:
            schema: dict[str, Any]
            if base_annotation in {str}:
                schema = {"type": "string"}
            elif base_annotation in {int}:
                schema = {"type": "integer"}
            elif base_annotation in {float}:
                schema = {"type": "number"}
            elif base_annotation in {bool}:
                schema = {"type": "boolean"}
            elif isinstance(base_annotation, type) and issubclass(base_annotation, BaseModel):
                schema = base_annotation.model_json_schema()
            elif base_annotation is Any:
                schema = {}
            else:
                schema = {"type": "string"}
        else:
            if origin is list:
                item_args = get_args(base_annotation)
                items_schema = annotation_to_schema(item_args[0]) if item_args else {}
                schema = {"type": "array", "items": items_schema}
            elif origin is dict:
                value_args = get_args(base_annotation)
                if value_args:
                    value_schema = annotation_to_schema(value_args[-1])
                else:
                    value_schema = {}
                schema = {"type": "object", "additionalProperties": value_schema}
            elif origin is tuple:
                arg_schemas = [annotation_to_schema(arg) for arg in get_args(base_annotation)]
                schema = {"type": "array", "prefixItems": arg_schemas}
            elif origin is set:
                item_args = get_args(base_annotation)
                items_schema = annotation_to_schema(item_args[0]) if item_args else {}
                schema = {"type": "array", "uniqueItems": True, "items": items_schema}
            elif origin is Literal:
                literal_args = list(get_args(base_annotation))
                schema = {"enum": literal_args}
                if literal_args and all(isinstance(arg, str) for arg in literal_args):
                    schema["type"] = "string"
                elif literal_args and all(isinstance(arg, bool) for arg in literal_args):
                    schema["type"] = "boolean"
                elif literal_args and all(isinstance(arg, int) for arg in literal_args):
                    schema["type"] = "integer"
            else:
                args = get_args(base_annotation)
                if origin is Union:
                    union_args = [arg for arg in args if arg is not NoneType]
                    if len(union_args) == 1:
                        schema = annotation_to_schema(union_args[0])
                    else:
                        schema = {"anyOf": [annotation_to_schema(arg) for arg in union_args]}
                else:
                    schema = {}

        if field_info:
            if field_info.description:
                schema["description"] = field_info.description
            if field_info.examples:
                schema["examples"] = list(field_info.examples)

        return schema

    signature = inspect.signature(func)
    type_hints = get_type_hints(func, include_extras=True)

    properties: dict[str, Any] = {}
    required: list[str] = []

    for name, param in signature.parameters.items():
        if name == "self":
            continue

        annotation = type_hints.get(name, Any)
        param_schema = annotation_to_schema(annotation)

        if param.default is not inspect._empty:
            param_schema.setdefault("default", param.default)
        else:
            if not is_optional(annotation):
                required.append(name)

        properties[name] = param_schema

    params_schema: dict[str, Any] = {"type": "object", "properties": properties, "additionalProperties": False}
    if required:
        params_schema["required"] = required

    return BaseTool(
        tool_name=func.__name__,
        description=func.__doc__ or "No description provided.",
        tool_params=params_schema,
        func=func
    )