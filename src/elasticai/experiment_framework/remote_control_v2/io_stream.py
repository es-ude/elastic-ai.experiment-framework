from abc import abstractmethod
from typing import Protocol


class IOStream(Protocol):
    def write(self, data: bytes | bytearray, /) -> int: ...

    def read(self, num_bytes: int, /) -> bytes | bytearray: ...
