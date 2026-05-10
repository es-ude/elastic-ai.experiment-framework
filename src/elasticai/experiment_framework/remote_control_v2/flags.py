from dataclasses import dataclass

@dataclass
class Flags:
    need_ack: bool = False
    has_crc:  bool = False
    
    def to_byte(self) -> int:
        value = 0
        if self.need_ack: value |= 0x01  # bit 0
        if self.has_crc:  value |= 0x02  # bit 1
        return value
    

    @classmethod
    def from_byte(cls, byte: int) -> "Flags":
        return cls(
            need_ack = bool(byte & 0x01),
            has_crc  = bool(byte & 0x02),
        )
    
    