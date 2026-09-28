import logging
import math

from ..remote_control.callback_actions import SendChunk
from ..remote_control.task import Task

logger = logging.getLogger(__name__)


class SimpleTask(Task):
    def __init__(
        self,
        task_def_id: int,
        data: bytes = b"",
        need_ack: bool = False,
        has_crc: bool = False,
    ):
        super().__init__(task_def_id)

        self._data = data
        self.need_ack = need_ack
        self.has_crc = has_crc

    @property
    def result(self) -> bytes:
        result = bytearray()
        for _, chunk in sorted(self.received_data.items()):
            result.extend(chunk)

        return bytes(result)

    async def on_opened(self):
        if self._data:
            yield SendChunk(self._data)


class FPGAInitTask(Task):
    def __init__(
        self,
        task_def_id: int,
        need_ack: bool = False,
        has_crc: bool = False,
    ):
        super().__init__(task_def_id)

        self.need_ack = need_ack
        self.has_crc = has_crc


class FPGAWriteToFlashTask(Task):
    def __init__(
        self,
        task_def_id: int,
        sector: int,
        data: bytes,
        chunk_size: int,
        need_ack: bool = False,
        has_crc: bool = False,
    ):
        super().__init__(task_def_id)

        self._data = data
        self.chunk_size = chunk_size
        self.sector = sector
        self.need_ack = need_ack
        self.has_crc = has_crc

    async def on_opened(self):
        yield SendChunk(
            int.to_bytes(
                self.sector,
                length=1,
                byteorder="little",
            ),
        )

        number_chunks = math.ceil(len(self._data) / self.chunk_size)

        for i in range(number_chunks):
            pos = i * self.chunk_size
            chunk = self._data[pos : pos + self.chunk_size]

            yield SendChunk(chunk)
