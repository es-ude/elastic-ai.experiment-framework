import asyncio
import logging
from typing import Callable, cast

from .io_stream import IOStream

_logger = logging.getLogger(__name__)


class TCPProtocolStream(asyncio.Protocol, IOStream):
    def __init__(self, on_lost: Callable):
        self._buffer = bytearray()
        self._waiter = None
        self._on_lost = on_lost
        self.transport: asyncio.Transport

    def connection_made(self, transport) -> None:
        self.transport = cast(asyncio.Transport, transport)

    def data_received(self, data: bytes) -> None:
        self._buffer.extend(data)

        if self._waiter and not self._waiter.done():
            self._waiter.set_result(None)

    def connection_lost(self, exc: Exception | None) -> None:
        return self._on_lost(exc)

    async def read(self, num_bytes: int) -> bytes:
        while len(self._buffer) < num_bytes:
            self._waiter = asyncio.get_running_loop().create_future()
            await self._waiter

        result = self._buffer[:num_bytes]
        del self._buffer[:num_bytes]
        return bytes(result)

    async def write(self, data: bytes | bytearray) -> None:  # type: ignore[override]
        _logger.debug(f"[CLIENT] write data  bytes {data}", stacklevel=2)

        self.transport.write(data)
