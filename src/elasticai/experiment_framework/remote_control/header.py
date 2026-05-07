import struct
from dataclasses import dataclass

from .commands import Command
from .constants import (
    HEADER_FORMAT,
    HEADER_SIZE,
    MAX_TASKS,
    SYNC_BYTE,
    MAX_PAYLOAD_lEN,
)
from .exceptions import (
    InvalidHeaderError,
    InvalidMsgIdError,
    InvalidPayloadLenError,
    InvalidTaskIdError,
)
from .flags import Flags


@dataclass
class Header:
    command: Command
    flags: Flags
    task_id: int
    msg_id: int
    payload_len: int

    def __post_init__(self) -> None:
        if not isinstance(self.command, Command):
            raise TypeError(f"expected Command, got {type(self.command)}")
        if not isinstance(self.flags, Flags):
            raise TypeError(f"expected Flags, got {type(self.flags)}")
        if not 0 <= self.msg_id <= MAX_TASKS:
            raise InvalidMsgIdError(f"msg_id out of range: {self.task_id}")
        if not 0 <= self.task_id <= MAX_TASKS:
            raise InvalidTaskIdError(f"task_id out of range: {self.task_id}")
        if not 0 <= self.payload_len <= MAX_PAYLOAD_lEN:
            raise InvalidPayloadLenError(
                f"payload_len out of range: {self.payload_len}"
            )

    def to_bytes(self) -> bytes:
        return struct.pack(
            HEADER_FORMAT,
            SYNC_BYTE,
            int(self.command),
            self.flags.to_byte(),
            self.task_id,
            self.msg_id,
            self.payload_len,
        )

    @classmethod
    def from_bytes(cls, data: bytes | bytearray) -> "Header":
        if len(data) != HEADER_SIZE:
            raise InvalidHeaderError(
                f"size short: need {HEADER_SIZE} bytes, got {len(data)}"
            )
        if data[0] != SYNC_BYTE:
            raise InvalidHeaderError(f"invalid sync byte: {data[0]:#x}")

        _, cmd, flags, task_id, msg_id, payload_len = struct.unpack_from(
            HEADER_FORMAT, data
        )
        return cls(
            command=Command.from_value(bytes([cmd])),
            flags=Flags.from_byte(flags),
            task_id=task_id,
            msg_id=msg_id,
            payload_len=payload_len,
        )

    def __repr__(self) -> str:
        return (
            f"Header(cmd={self.command.name}, "
            f"flags={self.flags}, "
            f"task_id={self.task_id}, "
            f"msg_id={self.msg_id}, "
            f"payload_len={self.payload_len})"
        )
