import logging
from typing import override

from elasticai.experiment_framework.remote_control.sync_remote_control import (
    SyncRemoteControl,
)

from ..remote_control.io_stream import IOStream
from .config import BYTE_ORDER, TaskDefinitionIds
from .tasks_registry import (
    FPGAInitTask,
    FPGAWriteToFlashTask,
    SimpleTask,
)

logger = logging.getLogger(__name__)


class SyncFPGARemoteControl(SyncRemoteControl):
    def __init__(self, device: IOStream):
        super().__init__(device)
        self._chunk_size = 0

    @override
    def initialize(self):
        task = FPGAInitTask(TaskDefinitionIds.FPGA_INIT)

        self._run_task(task)
        chunk_size = int.from_bytes(task.received_data[0])
        logger.info("chunk_size = %d", chunk_size)

        self._chunk_size = chunk_size

    def fpga_power_on(self):
        task = SimpleTask(TaskDefinitionIds.FPGA_POWER_ON)
        return self._run_task(task)

    def fpga_power_off(self):
        task = SimpleTask(TaskDefinitionIds.FPGA_POWER_OFF)
        return self._run_task(task)

    def read_skeleton_id(self) -> str:
        task = SimpleTask(TaskDefinitionIds.FPGA_READ_SKELETON_ID)

        self._run_task(task)

        return task.result.hex()

    def predict(
        self,
        data: bytes,
        result_size: int,
    ) -> bytes:
        task = SimpleTask(
            TaskDefinitionIds.FPGA_PREDICT,
            result_size.to_bytes(1, BYTE_ORDER) + data,
        )

        self._run_task(task)

        return task.result

    def upload_bitstream(
        self,
        flash_sector: int,
        path_to_bitstream: str,
        timer: bool = False,
        need_ack: bool = False,
        need_checksum: bool = False,
    ):
        with open(path_to_bitstream, "rb") as f:
            bitstream = f.read()

        task = FPGAWriteToFlashTask(
            task_def_id=TaskDefinitionIds.FPGA_WRITE_TO_FLASH if not timer else TaskDefinitionIds.FPGA_WRITE_TO_FLASH_TIMER,
            sector=flash_sector,
            data=bitstream,
            chunk_size=self._chunk_size,
            need_ack=need_ack,
            need_checksum=need_checksum,
        )

        self._run_task(task)
