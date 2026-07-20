from contextlib import asynccontextmanager

from ..remote_control.io_stream import IOStream
from ..remote_control.message_io import MessageIO
from ..remote_control.task import Task
from ..remote_control.task_manager import TaskManager
from .config import BYTE_ORDER, TaskDefinitionIds
from .tasks_registry import (
    FPGAInitTask,
    FPGAWriteToFlashTask,
    SimpleTask,
)


class FPGARemoteControl:
    def __init__(self, device: IOStream):
        self._manager = TaskManager(MessageIO(device))
        self._chunk_size = 0

    async def __aenter__(self):
        await self._manager.start()
        await self._initialize()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self._manager.stop()

    @asynccontextmanager
    async def _run_task(self, task: Task):
        await self._manager.open_task(task)
        try:
            yield task
        finally:
            await self._manager.close_task(task)

    async def _initialize(self):
        task = FPGAInitTask(TaskDefinitionIds.FPGA_INIT)

        async with self._run_task(task):
            pass

        self._chunk_size = task.chunk_size

    async def fpga_power_on(self):
        async with self._run_task(SimpleTask(TaskDefinitionIds.FPGA_POWER_ON)):
            pass

    async def fpga_power_off(self):
        async with self._run_task(SimpleTask(TaskDefinitionIds.FPGA_POWER_OFF)):
            pass

    async def read_skeleton_id(self) -> str:
        task = SimpleTask(TaskDefinitionIds.FPGA_READ_SKELETON_ID)

        async with self._run_task(task):
            pass

        return task.result.hex()

    async def predict(
        self,
        data: bytes,
        result_size: int,
    ) -> bytes:
        task = SimpleTask(
            TaskDefinitionIds.FPGA_PREDICT,
            result_size.to_bytes(1, BYTE_ORDER) + data,
        )

        async with self._run_task(task):
            pass

        return task.result

    async def upload_bitstream(
        self,
        flash_sector: int,
        path_to_bitstream: str,
    ):
        with open(path_to_bitstream, "rb") as f:
            bitstream = f.read()

        task = FPGAWriteToFlashTask(
            task_def_id=TaskDefinitionIds.FPGA_WRITE_TO_FLASH,
            sector=flash_sector,
            data=bitstream,
            chunk_size=self._chunk_size,
        )

        async with self._run_task(task):
            pass
