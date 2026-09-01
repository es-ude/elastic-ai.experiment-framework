import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, AsyncIterator

import serial_asyncio

from .constants import (
    NUM_MAX_RETRIES,
    RETRY_DELAY_SECONDS,
)
from .io_stream import IOStream
from .serial_protocol_stream import SerialTransportStream
from .tcp_protocol_stream import TCPProtocolStream

_logger = logging.getLogger(__name__)


class ConnectionProvider:
    def __init__(self, max_trials: int = NUM_MAX_RETRIES):
        self._max_trials = max_trials
        
    @asynccontextmanager
    async def connectTCP(
        self, host: str, port: int, max_trials: int | None = None
    ) -> AsyncGenerator[IOStream, None]:
        if max_trials is not None:
            self._max_trials = max_trials

        loop = asyncio.get_running_loop()

        protocol = None
        transport: asyncio.Transport | None = None

        for attempt in range(self._max_trials):
            try:

                def factory():
                    return TCPProtocolStream(self._on_lost)

                transport, protocol = await loop.create_connection(factory, host, port)

                _logger.debug("[CLIENT] connected via TCP")
                break

            except Exception as e:
                _logger.error(
                    f"[CLIENT] attempt TCP Connection {attempt + 1} failed: {e}"
                )
                await asyncio.sleep(RETRY_DELAY_SECONDS)

        else:
            _logger.error(f"[CLIENT] fail to connect after {self._max_trials}:")
            raise ConnectionError(f"[CLIENT] fail to connect after {self._max_trials}")

        try:
            yield protocol
        finally:
            if transport is not None:
                transport.close()

    @asynccontextmanager
    async def connectSerial(
        self, port: str, baudrate: int, max_trials: int | None = None
    ) -> AsyncGenerator[IOStream, None]:
        if max_trials is not None:
            self._max_trials = max_trials
        loop = asyncio.get_running_loop()

        protocol = None
        transport = None

        for attempt in range(self._max_trials):
            try:

                def factory():
                    return SerialTransportStream(self._on_lost)

                transport, protocol = await serial_asyncio.create_serial_connection(
                    loop, factory, port, baudrate
                )

                _logger.debug("[CLIENT] connected via Serial")
                break

            except Exception as e:
                _logger.error(
                    f"[CLIENT] attempt Serial Connection {attempt + 1} failed: {e}"
                )
                await asyncio.sleep(RETRY_DELAY_SECONDS)

        else:
            _logger.error(f"[CLIENT] fail to connect after {self._max_trials}:")

            raise ConnectionError(f"[CLIENT] fail to connect after {self._max_trials}")

        try:
            yield protocol
        finally:
            if transport is not None:
                transport.close()

    def _on_lost(self, exc):
        _logger.warning(f"connection lost: {exc}")
