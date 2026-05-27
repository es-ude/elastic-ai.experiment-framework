import asyncio
import logging

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

    async def connectTCP(
        self,
        host: str,
        port: int,
        max_trials: int = NUM_MAX_RETRIES,
    ) -> IOStream:
        loop = asyncio.get_running_loop()

        for attempt in range(max_trials):
            try:

                def factory():
                    return TCPProtocolStream(self._on_lost)

                _, _protocol = await loop.create_connection(factory, host, port)
                self._connected = True
                _logger.debug("[CLIENT] connected via TCP")

                return _protocol
            except Exception as e:
                _logger.error(f"[CLIENT] attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(RETRY_DELAY_SECONDS)
        _logger.error(f"[CLIENT] fail to connect after {max_trials}:")
        raise ConnectionError(f"[CLIENT] fail to connect after {max_trials}")

    def _on_lost(self, exc):
        _logger.warning(f"connection lost: {exc}")
