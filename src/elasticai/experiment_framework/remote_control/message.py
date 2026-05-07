from .commands import Command
from .constants import HEADER_SIZE
from .flags import Flags
from .header import Header


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
            flags=Flags.from_byte(flags),
            task_id=task_id,
            msg_id=msg_id,
            payload_len=len(payload),
        )
        self.payload = payload
        self.byte_order = byte_order

    def to_bytes(self) -> bytes:
        return self.header.to_bytes() + self.payload

    @classmethod
    def from_bytes(cls, raw: bytes, byte_order: str = "little") -> "Message":
        header = Header.from_bytes(raw[:HEADER_SIZE])

        payload = raw[HEADER_SIZE:]

        if len(payload) != header.payload_len:
            print(f" Message Header invalid, Hearder:{header}, Payload: {payload}")
            raise ValueError(f" Message Header invalid, Hearder:{header}")

        return cls(
            command=header.command,
            payload=payload,
            flags=header.flags.to_byte(),
            task_id=header.task_id,
            msg_id=header.msg_id,
            byte_order=byte_order,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Message):
            raise ValueError()
        return self.header == other.header and self.payload == other.payload

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
