# task_registry.py
from typing import Callable, Dict

from .task_definition import TaskDefinition


class TaskRegistry:
    def __init__(self) -> None:
        self._definitions: Dict[int, TaskDefinition] = {}

    def register(self, definition: TaskDefinition) -> None:
        self._definitions[definition.func_id] = definition

    def get(self, func_id: int) -> TaskDefinition:
        if func_id not in self._definitions:
            raise KeyError(f"no task defined for func_id={func_id}")
        return self._definitions[func_id]

    def task(self, func_id: int, **kwargs):
        """Decorator — define a task by decorating its on_opened handler."""

        def decorator(fn: Callable):
            self.register(TaskDefinition(func_id=func_id, on_opened=fn, **kwargs))
            return fn

        return decorator
