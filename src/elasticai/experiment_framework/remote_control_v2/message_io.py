from typing import Literal
import logging

from .commands import Command
from .io_stream import IOStream
from .message import Message
from .header import Header


class MessageIO:
    def __init__(
        self,
        io_stream:  IOStream,
        byte_order: Literal["big", "little"] = "little",
    ) -> None:
        self._stream     = io_stream
        self._byte_order: Literal["big", "little"]  = byte_order
        self._logger     = logging.getLogger(__name__)

    def read(self) -> Message:
        while True:
            byte = self._stream.read(1)
            if byte[0] == Header.SYNC_BYTE:
                break

        rest = self._stream.read(Header.SIZE - 1)
        header_bytes = bytes([Header.SYNC_BYTE]) + rest

        payload_len = int.from_bytes(
            header_bytes[4:6],
            byteorder=self._byte_order
        )

        payload = self._stream.read(payload_len)

        return Message.from_bytes(header_bytes + payload, byte_order=self._byte_order)

    def write(self, msg: Message) -> None:
        self._stream.write(msg.to_bytes())