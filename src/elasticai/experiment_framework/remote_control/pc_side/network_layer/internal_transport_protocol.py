import asyncio
import logging
from typing import Callable

from elasticai.experiment_framework.remote_control.pc_side.protocol.header import Header
from elasticai.experiment_framework.remote_control.pc_side.protocol.helpers import (
    format_message,
)
from elasticai.experiment_framework.remote_control.pc_side.protocol.message import (
    Message,
)

from ..protocol.constants import HEADER_SIZE, SYNC_BYTE

_logger = logging.getLogger(__name__)


class InternalTransportProtocolTCP(asyncio.Protocol):
    """
    Receives and sends messages to the remote peer.
    Only to be used for TCP connections.
    """

    def __init__(self, queue: asyncio.Queue[Message], on_lost: Callable) -> None:
        self.on_lost = on_lost
        self._buffer = bytearray()
        self._offset = 0
        self._queue = queue
        self._transport: asyncio.Transport
        _logger.debug("protocol initialized")

    def connection_made(self, transport: asyncio.Transport) -> None:
        self._transport = transport
        peer = transport.get_extra_info("peername")
        _logger.info("connection made with %s", peer)

    def connection_lost(self, exc: Exception | None) -> None:
        _logger.warning("connection lost: %s", exc)
        self.on_lost(exc)

    def data_received(self, data: bytes) -> None:
        _logger.debug("received %d %s bytes", len(data), data)
        self._buffer.extend(data)
        self._parse()

    def _parse(self) -> None:
        while len(self._buffer) - self._offset >= HEADER_SIZE:
            if self._buffer[self._offset] != SYNC_BYTE:
                _logger.warning(
                    "invalid sync byte at offset=%d value=%s",
                    self._offset,
                    hex(self._buffer[self._offset]),
                )
                self._offset += 1
                continue

            header_bytes = bytes(
                self._buffer[self._offset : self._offset + HEADER_SIZE]
            )

            try:
                header = Header.from_bytes(header_bytes)

            except ValueError as e:
                _logger.warning(
                    "invalid header at offset=%d: %s",
                    self._offset,
                    e,
                )
                self._offset += 1
                continue

            total_len = HEADER_SIZE + header.payload_len
            remaining = len(self._buffer) - self._offset

            if remaining < total_len:
                _logger.debug(
                    "incomplete message (have=%d expected=%d)",
                    remaining,
                    total_len,
                )
                break

            payload = bytes(
                self._buffer[self._offset + HEADER_SIZE : self._offset + total_len]
            )

            self._offset += total_len

            try:
                msg = Message.from_bytes(header_bytes + payload)

                _logger.debug(
                    "received message: %s",
                    format_message(msg),
                )

                self._queue.put_nowait(msg)

            except Exception:
                _logger.exception("failed to parse message")

        if self._offset > 0:
            _logger.debug(
                "consumed %d bytes from buffer",
                self._offset,
            )

        del self._buffer[: self._offset]
        self._offset = 0

    def write(self, data: bytes) -> None:

        if self._transport.is_closing():
            _logger.error("attempted write on closing transport")
            raise ConnectionError("_transport is closing")

        self._transport.write(data)

        try:
            msg = Message.from_bytes(data)

            _logger.debug(
                "sent message: %s",
                format_message(msg),
            )

        except Exception:
            _logger.debug("sent raw bytes len=%d", len(data))
