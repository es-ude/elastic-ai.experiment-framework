import math

from ..remote_control.callback_actions import SendChunk
from ..remote_control.task import Task


class SimpleTask(Task):
    def __init__(self, task_def_id: int, data: bytes = b""):
        super().__init__(task_def_id)
        self._data = data

    @property
    def result(self) -> bytes:
        result = bytearray()
        for _, chunk in sorted(self.received_data.items()):
            result.extend(chunk)

        return result

    async def on_opened(self):
        if self._data:
            yield SendChunk(self._data)


class FPGAInitTask(Task):
    def __init__(self, task_def_id: int):
        super().__init__(task_def_id=task_def_id)
        self.chunk_size = 0


class FPGAWriteToFlashTask(Task):
    def __init__(self, task_def_id: int, sector: int, data: bytes, chunk_size: int):
        super().__init__(task_def_id)
        self._data = data
        self.chunk_size = chunk_size
        self.sector = sector

    async def on_opened(self):
        yield SendChunk(int.to_bytes(self.sector, length=1, byteorder="little"))

        number_chunk = math.ceil(len(self._data) / self.chunk_size)

        for i in range(0, number_chunk):
            pos = i * self.chunk_size
            chunk = self._data[pos : pos + self.chunk_size]

            yield SendChunk(chunk)
