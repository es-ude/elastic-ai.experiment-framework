import logging
from typing import Literal

from crc import Calculator, Crc8

from .commands import Command
from .constants import HEADER_SIZE, NUM_BYTES_CHECKSUM
from .exceptions import (
    InvalidChecksumError,
    InvalidCommandPayloadError,
    InvalidPayloadLenError,
)
from .flags import Flags
from .header import Header
from .message_validators import validate_payload

_calculator = Calculator(Crc8.CCITT.value)

_logger = logging.getLogger(__name__)


class Message:
    def __init__(
        self,
        command: Command,
        payload: bytes,
        flags: int = 0,
        task_id: int = 0,
        msg_id: int = 0,
        byte_order: str = "little",
    ) -> None:
        self.header = Header(
            command=command,
            flags=Flags.from_number(flags),
            task_id=task_id,
            msg_id=msg_id,
            payload_len=len(payload),
        )
        self.payload = payload
        self.byte_order = byte_order
        self._checksum: int | None = None

    @property
    def checksum(self) -> int:
        if not self.header.flags.has_crc:
            raise ValueError("Message does not have a CRC.")

        if self._checksum is None:
            data = self.header.to_bytes() + self.payload
            self._checksum = _calculator.checksum(data)

        return self._checksum

    def to_bytes(self) -> bytes:
        data = self.header.to_bytes() + self.payload

        if self.header.flags.has_crc:
            data += int.to_bytes(self.checksum, NUM_BYTES_CHECKSUM)

        return data

    @classmethod
    def parse(
        cls, raw: bytes, byte_order: Literal["little", "big"] = "little"
    ) -> "Message":
        header = Header.from_bytes(raw[:HEADER_SIZE])
        payload = raw[HEADER_SIZE:]

        if header.flags.has_crc:
            if len(payload) < NUM_BYTES_CHECKSUM:
                raise InvalidPayloadLenError("message is missing its checksum")

            received_crc = int.from_bytes(
                payload[-NUM_BYTES_CHECKSUM:],
                byteorder=byte_order,
            )
            payload = payload[:-NUM_BYTES_CHECKSUM]
            message_without_crc = raw[:-NUM_BYTES_CHECKSUM]

        if len(payload) != header.payload_len:
            _logger.error(
                "[Client] Message payload length invalid, Header:%s, payload:%s",
                header,
                payload,
            )
            raise InvalidPayloadLenError(
                f"expected {header.payload_len} payload bytes, got {len(payload)}"
            )

        message = cls(
            command=header.command,
            payload=payload,
            flags=header.flags.to_number(),
            task_id=header.task_id,
            msg_id=header.msg_id,
            byte_order=byte_order,
        )

        if header.flags.has_crc and not _calculator.verify(
            message_without_crc, received_crc
        ):
            _logger.error(
                "[Client] Invalid checksum, Header:%s, Payload: %s checksum=%s ",
                header,
                payload,
                received_crc,
            )
            raise InvalidChecksumError(message)

        try:
            validate_payload(header.command, payload)
        except InvalidCommandPayloadError as exc:
            raise InvalidCommandPayloadError(str(exc), message) from exc

        return message

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Message):
            raise ValueError()
        return self.to_bytes() == other.to_bytes()

    def __repr__(self) -> str:
        return (
            f"Message("
            f"command={self.header.command.name}, "
            f"flags={self.header.flags}, "
            f"task_id={self.header.task_id}, "
            f"msg_id={self.header.msg_id}, "
            f"payload_len={len(self.payload)}, "
            f"payload={self.payload.hex() or '<empty>'}"
            f")"
        )
