# header.py
import struct
from dataclasses import dataclass
from .commands import Command
from .flags import Flags
from .constants import SYNC_BYTE, HEADER_SIZE

@dataclass
class Header:
    SYNC_BYTE = SYNC_BYTE
    SIZE      = HEADER_SIZE   

    command:     Command
    flags:       Flags
    msg_id:      int
    payload_len: int

    def to_bytes(self) -> bytes:
        return struct.pack("<BBBBH",
            self.SYNC_BYTE,
            int(self.command),
            self.flags.to_byte(),
            self.msg_id,
            self.payload_len,
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> "Header":
        if data[0] != cls.SYNC_BYTE:
            raise ValueError(f"Invalid sync: {data[0]:#x}")

        sync, cmd, flags, msg_id, payload_len = struct.unpack(
            "<BBBBH", data
        )
        return cls(
            command     = Command.from_bytes(bytes([cmd])),
            flags       = Flags.from_byte(flags),
            msg_id      = msg_id,
            payload_len = payload_len,
        )