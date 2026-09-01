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
)


class MessageIO:
    def __init__(self, stream: IOStream):
        self._stream = stream
        self._logger = logging.getLogger(__name__)

    async def _do_read(self, num_bytes) -> bytes:
        data = await self._stream.read(num_bytes)
        self._logger.debug(f"[CLIENT] read data {num_bytes} bytes {data}", stacklevel=2)
        return bytes(data)

    async def _sync(self) -> bytes:
        while True:
            b = await self._do_read(1)
            if b and b[0] == SYNC_BYTE:
                return b
            self._logger.warning("[CLIENT] resync: discarding byte %r", b)

    async def read(self) -> Message:
        sync = await self._sync()

        try:
            header_bytes = sync + await self._do_read(HEADER_SIZE - 1)
            header = Header.from_bytes(header_bytes)
        except HEADER_ERRORS as exc:
            self._logger.warning("[CLIENT] failed to parse header: %s", exc)
            
            raise MessageFramingError(
                "malformed header, stream will be resynced") from exc

        try:
            payload = await self._do_read(header.payload_len)

            checksum = b""
            if header.flags.has_crc:
                checksum = await self._do_read(NUM_BYTES_CHECKSUM)
                
            msg = Message.parse(header_bytes + payload+checksum)
            self._logger.debug(
                "[CLIENT] received message: %s", format_message(msg), stacklevel=3
            )
            return msg
        except MessageDecodeError:
            raise
        except Exception as exc:
            self._logger.warning("[CLIENT] failed to parse message: %s", exc)
            raise MessageFramingError(
                "malformed message, stream resynced to next sync byte"
            ) from exc

    async def write(self, msg: Message) -> None:
        self._logger.debug(
            "[CLIENT] sending message: %s", format_message(msg), stacklevel=3
        )
        await self._stream.write(msg.to_bytes())
