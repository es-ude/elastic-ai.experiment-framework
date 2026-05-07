from enum import IntEnum


class Command(IntEnum):
    OPEN_TASK = 0x01
    CLOSE_TASK = 0x02
    RETURN = 0x03
    DATA_CHUNK = 0x04
    ACK = 0x05
    NACK = 0x06
    HANDSHAKE = 0x07

    @classmethod
    def from_value(cls, data: bytes) -> "Command":
        value = int.from_bytes(data, byteorder="little")
        try:
            return cls(value)
        except ValueError:
            raise ValueError(f"Unknown command: {value:#x}")
