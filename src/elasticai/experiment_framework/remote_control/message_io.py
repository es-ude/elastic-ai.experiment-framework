import logging

from .constants import HEADER_SIZE
from .header import Header
from .helpers import format_message
from .io_stream import IOStream
from .message import Message


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

    async def read(self) -> Message:
        header_bytes = await self._do_read(HEADER_SIZE)
        self.raw_incoming_logger.debug(
            "[CLIENT] received header: %s", header_bytes.hex(), stacklevel=3
        )
        header = Header.from_bytes(header_bytes)

        payload = await self._do_read(header.payload_len)
        self.raw_incoming_logger.debug(
            "[CLIENT] received payload: %s", payload.hex(), stacklevel=3
        )

        msg = Message.from_bytes(header_bytes + payload)
        self.incoming_logger.debug(
            "[CLIENT] received message: %s", format_message(msg), stacklevel=3
        )

        return msg

    async def write(self, msg: Message) -> None:
        self.outgoing_logger.debug(
            "[CLIENT] sending message: %s", format_message(msg), stacklevel=3
        )
        await self._stream.write(msg.to_bytes())
