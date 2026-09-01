import logging

from .constants import HEADER_SIZE, NUM_BYTES_CHECKSUM, SYNC_BYTE
from .exceptions import (
    InvalidHeaderError,
    InvalidMsgIdError,
    InvalidPayloadLenError,
    InvalidTaskIdError,
    MessageDecodeError,
    MessageFramingError,
)
from .header import Header
from .helpers import format_message
from .io_stream import IOStream
from .message import Message

HEADER_ERRORS = (
    InvalidHeaderError,
    InvalidMsgIdError,
    InvalidPayloadLenError,
    InvalidTaskIdError,
    ValueError,
)


class MessageIO:
    incoming_logger = logging.getLogger(
        "elasticai.experiment_framework.remote_control.traffic.message.incoming"
    )
    outgoing_logger = logging.getLogger(
        "elasticai.experiment_framework.remote_control.traffic.message.outgoing"
    )
    raw_incoming_logger = logging.getLogger(
        "elasticai.experiment_framework.remote_control.traffic.raw.incoming"
    )

    def __init__(self, stream: IOStream):
        self._stream = stream

    async def _do_read(self, num_bytes) -> bytes:
        data = await self._stream.read(num_bytes)
        self.raw_incoming_logger.debug(
            f"[CLIENT] read data {num_bytes} bytes {data}", stacklevel=2
        )
        return bytes(data)

    async def _sync(self) -> bytes:
        while True:
            b = await self._do_read(1)
            if b and b[0] == SYNC_BYTE:
                return b
            self.incoming_logger.warning("[CLIENT] resync: discarding byte %r", b)

    async def read(self) -> Message:
        sync = await self._sync()

        try:
            header_bytes = sync + await self._do_read(HEADER_SIZE - 1)
            header = Header.from_bytes(header_bytes)
        except HEADER_ERRORS as exc:
            self.raw_incoming_logger.debug(
            "[CLIENT] received header: %s", header_bytes.hex(), stacklevel=3
        )

            raise MessageFramingError(
                "malformed header, stream will be resynced"
            ) from exc

        try:
            payload = await self._do_read(header.payload_len)

            checksum = b""
            if header.flags.has_crc:
                checksum = await self._do_read(NUM_BYTES_CHECKSUM)

            msg = Message.parse(header_bytes + payload + checksum)
            self.incoming_logger.debug(
                "[CLIENT] received message: %s", format_message(msg), stacklevel=3
            )
            return msg
        except MessageDecodeError:
            raise
        except Exception as exc:
            self.incoming_logger.warning("[CLIENT] failed to parse message: %s", exc)
            raise MessageFramingError(
                "malformed message, stream will resynced to next sync byte"
            ) from exc

    async def write(self, msg: Message) -> None:
        self.outgoing_logger.debug(
            "[CLIENT] sending message: %s", format_message(msg), stacklevel=3
        )
        await self._stream.write(msg.to_bytes())
