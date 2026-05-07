import asyncio
import logging
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict

from elasticai.experiment_framework.remote_control.pc_side.network_layer.connection import (
    Connection,
)
from elasticai.experiment_framework.remote_control.pc_side.protocol.exceptions import (
    UnexpectedMessageError,
)
from elasticai.experiment_framework.remote_control.pc_side.protocol.message import (
    Message,
)

_logger = logging.getLogger(__name__)


@dataclass
class MessageExpectation:
    transaction_id: int
    callback: Callable[[Message], Awaitable[None]]


class DeviceSession:
    """Owns one device connection — routes messages, nothing else."""

    def __init__(
        self, session_id: int, device_info: dict, connection: Connection
    ) -> None:
        self.id: int = session_id
        self.device_info: dict = device_info
        self.connection: Connection = connection
        self._expectations: Dict[int, MessageExpectation] = {}
        self._task: asyncio.Task
        self._started = asyncio.Event()

    async def start(self):
        self._task = asyncio.create_task(self._receive_loop())
        await self._started.wait()

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            await self.connection.close()

    def expect(self, transaction_id: int, callback: Callable) -> None:
        """Register a callback for an incoming transaction_id."""
        self._expectations[transaction_id] = MessageExpectation(
            transaction_id, callback
        )

    async def _receive_loop(self) -> None:
        self._running = True
        self._started.set()

        while self._running:
            try:
                message = await self.connection.receive(timeout=None)
                await self._dispatch(message)

            except TimeoutError:
                _logger.warning("[CLIENT]device %d timed out", self.id)
                self._running = False

            except Exception as e:
                _logger.error("[CLIENT]device %d receive error: %s", self.id, e)
                self._running = False

    async def _dispatch(self, message: Message) -> None:
        tid = message.header.transaction_id
        exp = self._expectations.get(tid, None)

        if exp is not None:
            await exp.callback(message)
        else:
            _logger.warning("[CLIENT]device %d unhandled message tid=%d", self.id, tid)
            raise UnexpectedMessageError
