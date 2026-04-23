from typing import Self
from dataclasses import dataclass

"""
Frame format:

| Byte  | Meaning                |
+-------+------------------------+
| 1     | MSB 1 -> ACK Required  |
|       | MSB 0 -> ACK disabled  |
|       | Other bits identify    |
|       | frame type             |
+-------+------------------------+
| 2-3   | Payload Size Big-Endian|
+-------+------------------------+
| 4-N.  | Payload                |
+-------+------------------------+
| N+1.  | Checksum (Only if ACK  |
|       |            Required)   |
+-------+------------------------+

Frame Types:

 - `0x00`: `ACK`
 - `0x01`: `NACK`

"""


@dataclass(frozen=True)
class Frame:
    raw_data: bytes
    requires_checksum: bool
    payload: bytes


class FrameBuilder:
    def __init__(self) -> None:
        self._require_checksum = False
        self._payload = bytes()

    def requireChecksum(self) -> Self:
        self._require_checksum = True
        return self

    def setPayload(self, data: bytes) -> Self:
        self._payload = data
        return self

    def _compute_checksum(self, raw: bytes | bytearray) -> int:
        checksum = 0
        for b in raw:
            checksum ^= b
        return checksum

    def build(self) -> Frame:
        size = len(self._payload)
        raw = bytearray()
        if self._require_checksum:
            raw.append(0x01)
        else:
            raw.append(0x00)
        raw.extend(size.to_bytes(length=2, byteorder="big"))
        raw.extend(self._payload)
        raw.append(self._compute_checksum(raw))
        raw = bytes(raw)
        return Frame(raw, self._require_checksum, raw[3:-1])


class FrameWriter:
    def __init__(self, memory: bytearray) -> None:
        self._memory = memory

    def has_finished(self) -> bool:
        return True

    def write(self, data: bytes | int) -> None:
        if isinstance(data, int):
            self._memory.append(data)
        else:
            self._memory.extend(data)
