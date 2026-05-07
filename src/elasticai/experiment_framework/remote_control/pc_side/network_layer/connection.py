import asyncio
import logging

from elasticai.experiment_framework.remote_control.pc_side.protocol.message import (
    Message,
)

from ..protocol.constants import (
    CONNECTION_TIMEOUT_SECONDS,
    NUM_MAX_RETRIES,
    RETRY_DELAY_SECONDS,
    TransportType,
)
from .internal_transport_protocol import InternalTransportProtocolTCP

_logger = logging.getLogger(__name__)


class Connection:
    def __init__(
        self,
        transportType: TransportType,
        host=None,
        port=None,
        serial_port=None,
        baudrate=115200,
    ):
        self._transport_type = transportType
        self._host = host
        self._port = port
        self._serial_port = serial_port
        self._baudrate = baudrate

        self._queue: asyncio.Queue[Message] = asyncio.Queue()
        self._protocol: InternalTransportProtocolTCP
        self._connected = False
        self._timeout = CONNECTION_TIMEOUT_SECONDS
        self._timeout_handle = None

    async def connect(self):
        loop = asyncio.get_running_loop()

        for attempt in range(NUM_MAX_RETRIES):
            try:
                await self._create_connection(loop)
                self._connected = True
                print(f"connected via {self._transport_type}")
                _logger.debug(f"[CLIENT] connected via {self._transport_type}")
                return
            except Exception as e:
                print(f"attempt {attempt + 1} failed: {e}")
                _logger.error(f"[CLIENT] attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(RETRY_DELAY_SECONDS)

        raise ConnectionError("could not connect after retries")

    async def _create_connection(self, loop):
        if self._transport_type == TransportType.TCP:

            def factory():
                return InternalTransportProtocolTCP(self._queue, self._on_lost)

            _, self._protocol = await loop.create_connection(
                factory, self._host, self._port
            )

        else:
            raise NotImplementedError(
                f"transport type {self._transport_type} not supported yet"
            )

    def _on_lost(self, exc):
        self._connected = False
        self._cancel_timeout()
        print(f"connection lost: {exc}")
        _logger.warning(f"connection lost: {exc}")
        asyncio.create_task(self.connect())

    async def send(self, message: bytes | bytearray):
        if not self._connected:
            raise ConnectionError("not connected")

        self._protocol.write(message)

    async def receive(self, timeout=None) -> Message:
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=None)
        except asyncio.TimeoutError:
            raise TimeoutError("no message received in time")

    async def close(self):
        self._cancel_timeout()
        if self._protocol:
            self._protocol._transport.close()
        self._connected = False

    def _cancel_timeout(self):
        if self._timeout_handle:
            self._timeout_handle.cancel()
            self._timeout_handle = None
