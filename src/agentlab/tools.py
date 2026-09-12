from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, get_args, get_origin, get_type_hints
import inspect

VALID_TOOL_STATUSES = {"COMMITTED", "NOT_APPLIED", "UNKNOWN"}


@dataclass(slots=True)
class ToolResult:
    ok: bool
    value: Any = None
    error: str | None = None
    status: str = "COMMITTED"  # COMMITTED | NOT_APPLIED | UNKNOWN
    retryable: bool = False

    def to_message(self) -> dict[str, Any]:
        return {
            "role": "tool",
            "ok": self.ok,
            "value": self.value,
            "error": self.error,
            "status": self.status,
            "retryable": self.retryable,
        }


def tool(description: str = "", *, risk: str = "low", idempotent: bool = True):
    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        fn._agentlab_tool = True  # type: ignore[attr-defined]
        fn._agentlab_description = description or fn.__doc__ or ""  # type: ignore[attr-defined]
        fn._agentlab_risk = risk  # type: ignore[attr-defined]
        fn._agentlab_idempotent = idempotent  # type: ignore[attr-defined]
        return fn

    return deco


def _json_type(t: Any) -> dict[str, Any]:
    origin = get_origin(t)
    if origin is list:
        args = get_args(t)
        return {"type": "array", "items": _json_type(args[0] if args else str)}
    if origin is dict:
        return {"type": "object"}
    if t in (int,):
        return {"type": "integer"}
    if t in (float,):
        return {"type": "number"}
    if t in (bool,):
        return {"type": "boolean"}
    return {"type": "string"}


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., Any]] = {}

    def register(self, fn: Callable[..., Any], name: str | None = None) -> None:
        self._tools[name or fn.__name__] = fn

    def contains(self, name: str) -> bool:
        return name in self._tools

    def metadata(self, name: str) -> dict[str, Any]:
        fn = self._tools[name]
        return {"risk": getattr(fn, "_agentlab_risk", "low"), "idempotent": getattr(fn, "_agentlab_idempotent", True)}

    def metadata_or_default(self, name: str) -> dict[str, Any]:
        if name not in self._tools:
            return {"risk": "unknown", "idempotent": False}
        return self.metadata(name)

    def schema(self) -> list[dict[str, Any]]:
        result = []
        for name, fn in self._tools.items():
            sig = inspect.signature(fn)
            hints = get_type_hints(fn)
            props: dict[str, Any] = {}
            required: list[str] = []
            for p in sig.parameters.values():
                props[p.name] = _json_type(hints.get(p.name, str))
                if p.default is inspect._empty:
                    required.append(p.name)
            result.append(
                {
                    "name": name,
                    "description": getattr(fn, "_agentlab_description", ""),
                    "risk": getattr(fn, "_agentlab_risk", "low"),
                    "idempotent": getattr(fn, "_agentlab_idempotent", True),
                    "parameters": {"type": "object", "properties": props, "required": required},
                }
            )
        return result

    def execute(self, name: str, args: dict[str, Any]) -> ToolResult:
        if name not in self._tools:
            return ToolResult(False, error=f"unknown_tool:{name}", status="NOT_APPLIED", retryable=False)
        fn = self._tools[name]
        idempotent = bool(getattr(fn, "_agentlab_idempotent", True))
        try:
            inspect.signature(fn).bind(**args)
            value = fn(**args)
            result = value if isinstance(value, ToolResult) else ToolResult(True, value=value)
            if result.status not in VALID_TOOL_STATUSES:
                return ToolResult(
                    False, error=f"invalid_tool_status:{result.status}", status="UNKNOWN", retryable=False
                )
            # UNKNOWN never becomes safe merely because an exception was transient.
            # A retry hint is allowed only when the tool contract itself declares
            # idempotency. The runtime still requires reconciliation before retry.
            if result.status == "UNKNOWN" and not idempotent:
                result.retryable = False
            return result
        except TypeError as e:
            return ToolResult(False, error=f"bad_arguments:{e}", status="NOT_APPLIED", retryable=False)
        except TimeoutError as e:
            return ToolResult(False, error=f"timeout:{e}", status="UNKNOWN", retryable=idempotent)
        except Exception as e:
            return ToolResult(False, error=f"tool_exception:{type(e).__name__}:{e}", status="UNKNOWN", retryable=False)
