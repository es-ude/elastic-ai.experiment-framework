from dataclasses import dataclass


@dataclass
class Flags:
    need_ack: bool = False
    has_crc: bool = False

    _NEED_ACK_BIT = 0
    _HAS_CRC_BIT = 1

    def to_byte(self) -> int:
        value = 0
        if self.need_ack:
            value |= 1 << self._NEED_ACK_BIT
        if self.has_crc:
            value |= 1 << self._HAS_CRC_BIT
        return value

    @classmethod
    def from_byte(cls, byte: int) -> "Flags":
        return cls(
            need_ack=bool(byte & (1 << cls._NEED_ACK_BIT)),
            has_crc=bool(byte & (1 << cls._HAS_CRC_BIT)),
        )
