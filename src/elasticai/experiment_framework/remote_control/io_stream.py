from abc import ABC, abstractmethod


class IOStream(ABC):
    @abstractmethod
    async def write(self, data: bytes | bytearray, /) -> int: ...

    @abstractmethod
    async def read(self, num_bytes: int, /) -> bytes | bytearray: ...
