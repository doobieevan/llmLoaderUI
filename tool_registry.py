"""Small allowlist-driven extension point for assistant tools."""

import re
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    mode: str
    fields: tuple[str, ...]


class ToolRegistry:
    """Tools execute only through application-registered Python handlers."""

    def __init__(self):
        self._specs = {}
        self._handlers = {}

    def register(self, spec: ToolSpec, handler: Callable):
        if (not isinstance(spec, ToolSpec) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", spec.name)
                or spec.name in self._specs or not callable(handler)):
            raise ValueError("Tool name must be valid and unique, with a callable handler.")
        if spec.mode not in {"read", "workspace_write", "command"}:
            raise ValueError("Unsupported tool permission class.")
        if (not isinstance(spec.description, str) or not isinstance(spec.fields, tuple)
                or any(not isinstance(field, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", field) for field in spec.fields)
                or len(set(spec.fields)) != len(spec.fields)):
            raise ValueError("Tool description and required fields must be valid.")
        self._specs[spec.name] = spec
        self._handlers[spec.name] = handler

    def describe(self):
        return [
            {"tool": spec.name, "description": spec.description, "required_fields": list(spec.fields)}
            for spec in self._specs.values()
        ]

    def authorize(self, name, action, permission_mode, command_is_allowlisted=False, auto_approve_workspace=False):
        spec = self._specs.get(name)
        if spec is None or not isinstance(action, dict) or action.get("tool") != name:
            return "deny"
        if not all(isinstance(action.get(field), str) for field in spec.fields):
            return "deny"
        if set(action) - ({"tool"} | set(spec.fields)):
            return "deny"
        if spec.mode == "read":
            return "allow"
        if permission_mode == "Read-Only":
            return "deny"
        if spec.mode == "workspace_write":
            return "allow" if permission_mode == "Auto (Workspace)" or auto_approve_workspace else "confirm"
        if spec.mode == "command":
            if permission_mode == "Auto (Workspace)" or auto_approve_workspace:
                return "allow" if command_is_allowlisted else "deny"
            return "confirm" if permission_mode == "Ask Before Acting" else "deny"
        return "deny"

    def execute(self, name, action, permission_mode, command_is_allowlisted=False, auto_approve_workspace=False):
        decision = self.authorize(name, action, permission_mode, command_is_allowlisted, auto_approve_workspace)
        if decision != "allow":
            raise PermissionError(f"Tool {name!r} is not automatically authorized ({decision}).")
        return self._handlers[name](action)


def default_registry(handlers=None):
    registry = ToolRegistry()
    handlers = handlers or {}

    def unavailable(_action):
        raise RuntimeError("No application handler is registered for this tool.")

    registry.register(ToolSpec("read_file", "Read a small UTF-8 file inside the selected workspace.", "read", ("path",)), handlers.get("read_file", unavailable))
    registry.register(ToolSpec("list_files", "List names inside the selected workspace.", "read", ()), handlers.get("list_files", unavailable))
    registry.register(ToolSpec("docker_ps", "Show docker ps -a output.", "read", ()), handlers.get("docker_ps", unavailable))
    registry.register(ToolSpec("write_file", "Write text to a workspace-relative file.", "workspace_write", ("path", "content")), handlers.get("write_file", unavailable))
    registry.register(ToolSpec("run_command", "Run a fixed safe check or request approval for another command.", "command", ("command",)), handlers.get("run_command", unavailable))
    return registry
