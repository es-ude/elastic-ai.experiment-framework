# header.py
import struct
from dataclasses import dataclass
from .commands import Command
from .flags import Flags
from .constants import SYNC_BYTE, HEADER_FORMAT, HEADER_SIZE, MAX_TRANSACTIONS


@dataclass
class Header:
    command: Command
    flags: Flags
    transaction_id: int
    payload_len: int

    @property
    def total_size(self) -> int:
        """Full message size including payload"""
        return HEADER_SIZE + self.payload_len

    @property
    def get_command(self):
        return self.command

    @property
    def get_flages(self):
        return self.flags

    @property
    def get_transaction_id(self):
        return self.transaction_id

    @property
    def get_payload_len(self):
        return self.payload_len

    def __post_init__(self) -> None:
        if not isinstance(self.command, Command):
            raise TypeError(f"expected Command, got {type(self.command)}")
        if not isinstance(self.flags, Flags):
            raise TypeError(f"expected Flags, got {type(self.flags)}")
        if not 0 <= self.transaction_id <= MAX_TRANSACTIONS:
            raise ValueError(f"transaction_id out of range: {self.transaction_id}")
        if self.payload_len < 0:
            raise ValueError(f"payload_len cannot be negative: {self.payload_len}")

    def to_bytes(self) -> bytes:
        return struct.pack(
            HEADER_FORMAT,
            SYNC_BYTE,
            int(self.command),
            self.flags.to_byte(),
            self.transaction_id,
            self.payload_len,
        )

    @classmethod
    def from_bytes(cls, data: bytes | bytearray | memoryview) -> "Header":
        if len(data) < HEADER_SIZE:
            raise ValueError(f"too short: need {HEADER_SIZE} bytes, got {len(data)}")
        if data[0] != SYNC_BYTE:
            raise ValueError(f"invalid sync byte: {data[0]:#x}")

        _, cmd, flags, transaction_id, payload_len = struct.unpack_from(
            HEADER_FORMAT, data
        )
        return cls(
            command=Command.from_bytes(bytes([cmd])),
            flags=Flags.from_byte(flags),
            transaction_id=transaction_id,
            payload_len=payload_len,
        )

    def __repr__(self) -> str:
        return (
            f"Header(cmd={self.command.name}, "
            f"flags={self.flags}, "
            f"tid={self.transaction_id}, "
            f"payload_len={self.payload_len})"
        )
