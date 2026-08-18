import logging

from ..remote_control.constants import SUCCESS_CODE
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

logger = logging.getLogger(__name__)

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

    async def _run_task(self, task: Task):
        await self._manager.open_task(task)
        try:
            return_code = await task.wait_for_return()
        
            if return_code != SUCCESS_CODE:
                raise RuntimeError(
                    f"Remote task {task.task_id} failed with code {return_code}"
                )

            return return_code
        finally:
            await self._manager.close_task(task)

    async def _initialize(self):
        task = FPGAInitTask(TaskDefinitionIds.FPGA_INIT)

        await self._run_task(task)
        chunk_size = int.from_bytes(task.received_data[0])
        logger.info("chunk_size = %d", chunk_size)
        
        self._chunk_size = chunk_size

    async def fpga_power_on(self):
        task = SimpleTask(TaskDefinitionIds.FPGA_POWER_ON)
        return await self._run_task(task)


    async def fpga_power_off(self):
        task = SimpleTask(TaskDefinitionIds.FPGA_POWER_OFF)
        return await self._run_task(task)


    async def read_skeleton_id(self) -> str:
        task = SimpleTask(TaskDefinitionIds.FPGA_READ_SKELETON_ID)

        await self._run_task(task)

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

        await self._run_task(task)

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

        await self._run_task(task)


        
