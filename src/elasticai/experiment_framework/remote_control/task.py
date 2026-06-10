import asyncio
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import AsyncGenerator, Dict

from elasticai.experiment_framework.remote_control.constants import (
    RESPONSE_TIMEOUT,
)

from .callback_actions import CallbackAction


class TaskState(Enum):
    OPENING = auto()
    OPENED = auto()
    RECEIVED_DATA = auto()
    RETURNED = auto()
    CLOSING = auto()
    CLOSED = auto()


class Task(ABC):
    def __init__(self) -> None:
        self.timeout: float = RESPONSE_TIMEOUT
        self.need_ack: bool = False
        self.func_id: int = 0

        self._transaction_id: int = 0
        self._state: TaskState = TaskState.OPENING
        self._opened_event: asyncio.Event = asyncio.Event()
        self._finished_event: asyncio.Event = asyncio.Event()
        self._closed_event: asyncio.Event = asyncio.Event()
        self._next_data_id: int = 0
        self._received_data: dict[int, bytes] = {}
        self._pending_acks: Dict[int, asyncio.Future] = {}

    @property
    def transaction_id(self) -> int:
        return self._transaction_id

    @property
    def state(self) -> TaskState:
        return self._state

    @property
    def received_data(self) -> dict[int, bytes]:
        return self._received_data

    async def on_opened(self) -> AsyncGenerator[CallbackAction, None]:
        return
        yield

    @abstractmethod
    async def on_data_chunk_received(self) -> AsyncGenerator[CallbackAction, None]:
        return
        yield

    @abstractmethod
    async def on_return(self) -> AsyncGenerator[CallbackAction, None]:
        return
        yield
