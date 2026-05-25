from abc import abstractmethod
from typing import Protocol


class IOStream(Protocol):
    @abstractmethod
    async def write(self, data: bytes | bytearray, /) -> int: ...

    @abstractmethod
    async def read(self, num_bytes: int, /) -> bytes | bytearray: ...