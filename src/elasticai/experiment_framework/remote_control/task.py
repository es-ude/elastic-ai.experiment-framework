import asyncio
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import AsyncGenerator, Dict

from elasticai.experiment_framework.remote_control.constants import (
    RESPONSE_TIMEOUT,
)

from .callback_actions import CallbackAction, NoAction


class TaskState(Enum):
    INITIAL = auto()
    OPENING = auto()
    OPENED = auto()
    RECEIVED_DATA = auto()
    RETURNED = auto()
    CLOSING = auto()
    CLOSED = auto()


class Task(ABC):
    def __init__(self, task_def_id: int) -> None:
        self.timeout: float = RESPONSE_TIMEOUT
        self.need_ack: bool = False
        self.task_def_id: int = task_def_id

        self._task_id: int = 0
        self._state: TaskState = TaskState.OPENING
        self._return_code: int | None = None
        self._returned_event = asyncio.Event()
        self._state: TaskState = TaskState.INITIAL
        self._next_msg_id: int = 0
        self._completion: asyncio.Future[int] | None = None
        self._received_data: dict[int, bytes] = {}
        self._pending_acks: Dict[int, asyncio.Future] = {}

    @property
    def task_id(self) -> int:
        return self._task_id

    @property
    def state(self) -> TaskState:
        return self._state

    @property
    def received_data(self) -> dict[int, bytes]:
        return self._received_data

    async def wait_for_return(self) -> int:
        if self._completion is None:
            raise RuntimeError("Task has not been opened")

        return await asyncio.wait_for(
            asyncio.shield(self._completion),
            timeout=self.timeout,
        )

    async def on_opened(self) -> AsyncGenerator[CallbackAction, None]:
        yield NoAction()

    @abstractmethod
    async def on_data_chunk_received(self) -> AsyncGenerator[CallbackAction, None]:
        yield NoAction()

    @abstractmethod
    async def on_return(self) -> AsyncGenerator[CallbackAction, None]:
        yield NoAction()
