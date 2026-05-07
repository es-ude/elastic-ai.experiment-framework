import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from .constants import (
    NUM_MAX_RETRIES,
    RETRY_DELAY_SECONDS,
)
from .io_stream import IOStream
from .tcp_protocol_stream import TCPProtocolStream

_logger = logging.getLogger(__name__)


class ConnectionProvider:
    def __init__(self, max_trials: int = NUM_MAX_RETRIES):
        self._max_trials = max_trials

    @asynccontextmanager
    async def connectTCP(
        self, host: str, port: int, max_trials: int | None = None
    ) -> AsyncIterator[IOStream]:
        if max_trials is not None:
            self._max_trials = max_trials
        loop = asyncio.get_running_loop()

        protocol = None

        for attempt in range(self._max_trials):
            try:

                def factory():
                    return TCPProtocolStream(self._on_lost)

                _, protocol = await loop.create_connection(factory, host, port)

                _logger.debug("[CLIENT] connected via TCP")
                break

            except Exception as e:
                _logger.error(f"[CLIENT] attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(RETRY_DELAY_SECONDS)

        else:
            _logger.error(f"[CLIENT] fail to connect after {self._max_trials}:")

            raise ConnectionError(f"[CLIENT] fail to connect after {self._max_trials}")

        try:
            yield protocol
        finally:
            protocol.transport.close()

    def _on_lost(self, exc):
        _logger.warning(f"connection lost: {exc}")
