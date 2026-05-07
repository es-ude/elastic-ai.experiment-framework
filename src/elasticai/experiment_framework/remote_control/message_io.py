import logging

from .constants import HEADER_SIZE
from .header import Header
from .helpers import format_message
from .io_stream import IOStream
from .message import Message


class MessageIO:
    def __init__(self, stream: IOStream):
        self._stream = stream
        self._logger = logging.getLogger(__name__)

    async def _do_read(self, num_bytes) -> bytes:
        self._logger.debug(f"[CLIENT] {num_bytes} bytes", stacklevel=2)
        data = await self._stream.read(num_bytes)
        self._logger.debug(f"[CLIENT] read data {data}", stacklevel=2)
        return bytes(data)

    async def read(self) -> Message:
        header_bytes = await self._do_read(HEADER_SIZE)
        self._logger.debug(
            "[CLIENT] received header: %s", header_bytes.hex(), stacklevel=3
        )
        header = Header.from_bytes(header_bytes)

        payload = await self._do_read(header.payload_len)
        self._logger.debug("[CLIENT] received payload: %s", payload.hex(), stacklevel=3)

        msg = Message.from_bytes(header_bytes + payload)
        self._logger.debug(
            "[CLIENT] received message: %s", format_message(msg), stacklevel=3
        )

        return msg

    async def write(self, msg: Message) -> None:
        self._logger.debug(
            "[CLIENT] sending message: %s", format_message(msg), stacklevel=3
        )
        await self._stream.write(msg.to_bytes())
