import asyncio
import logging
from typing import Callable, cast

from .io_stream import IOStream

_logger = logging.getLogger(
    "elasticai.experiment_framework.remote_control.traffic.raw.outgoing"
)


class SerialTransportStream(asyncio.Protocol, IOStream):
    def __init__(self, on_lost: Callable):
        self._buffer = bytearray()
        self._on_lost = on_lost
        self._waiter: asyncio.Future | None = None
        self.transport: asyncio.Transport

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = cast(asyncio.Transport, transport)

    def connection_lost(self, exc: Exception | None) -> None:
        if self._waiter is not None and not self._waiter.done():
            self._waiter.set_exception(exc or ConnectionError("connection lost"))
        self._on_lost(exc)

    def data_received(self, data: bytes) -> None:
        self._buffer.extend(data)
        self.pause_reading()
        if self._waiter is not None and not self._waiter.done():
            self._waiter.set_result(None)

    def pause_reading(self):
        self.transport.pause_reading()

    def resume_reading(self):
        self.transport.resume_reading()

    async def read(self, num_bytes: int) -> bytes:
        while len(self._buffer) < num_bytes:
            self._waiter = asyncio.get_running_loop().create_future()
            self.resume_reading()
            await self._waiter

        result = bytes(self._buffer[:num_bytes])
        del self._buffer[:num_bytes]
        return result

    async def write(self, data: bytes | bytearray) -> None:  # type: ignore[override]
        if self.transport is None:
            raise RuntimeError("write() called before connection established")

        _logger.debug(f"[CLIENT] write data  bytes {data}", stacklevel=2)

        self.transport.write(data)
