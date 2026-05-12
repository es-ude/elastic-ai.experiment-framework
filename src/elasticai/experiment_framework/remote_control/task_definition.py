# task_definition.py
from dataclasses import dataclass, field
from typing import Callable, Awaitable, Optional

from elasticai.experiment_framework.remote_control.task_context import TaskContext


SendChunk = Callable[[bytes], Awaitable[None]]

@dataclass
class TaskDefinition:
    func_id: int
    on_opened:     Optional[Callable[["TaskContext", SendChunk], Awaitable[None]]] = None 
    on_data_chunk_received: Optional[Callable[["TaskContext", bytes], Awaitable[None]]] = None
    on_is_last: Optional[Callable[["TaskContext"], Awaitable[None]]] = None
    on_finished:   Optional[Callable[["TaskContext"],Awaitable[None]]] = None

    need_ack: bool = False 
    timeout: float = 5.0