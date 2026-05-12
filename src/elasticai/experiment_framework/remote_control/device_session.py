# device_session.py
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Callable, Dict

from elasticai.experiment_framework.remote_control.message import Message

from .commands import Command
from elasticai.experiment_framework.remote_control.network_layer.connection import Connection

_logger = logging.getLogger(__name__)

@dataclass
class MessageExpectation:
    transaction_id: int
    callback:       Callable[[Message], None]

class DeviceSession:
    """Owns one device connection — routes messages, nothing else."""

    def __init__(self, session_id: int, device_info: dict, connection: Connection) -> None:
        self.id:           int        = session_id
        self.device_info:  dict       = device_info
        self.connection:   Connection = connection
        self._expectations: Dict[int, MessageExpectation] = {}
        self._task:         asyncio.Task | None = None


    def start(self) -> None:
        self._task = asyncio.create_task(self._receive_loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            await self.connection.close()


    def expect(self, transaction_id: int, callback: Callable) -> None:
        """Register a callback for an incoming transaction_id."""
        self._expectations[transaction_id] = MessageExpectation(transaction_id, callback)

    async def _receive_loop(self) -> None:
        while True:
            try:
                message = await self.connection.receive(timeout =None)
                self._dispatch(message)

            except TimeoutError:
                _logger.warning("device %d timed out", self.id)
                break

            except Exception as e:
                _logger.error("device %d receive error: %s", self.id, e)
                break

    def _dispatch(self, message: Message) -> None:
        tid = message.header.get_transaction_id
        exp = self._expectations.get(tid, None)

        if exp is not None:
            exp.callback(message)
        else:
            _logger.warning("device %d unhandled message tid=%d", self.id, tid)