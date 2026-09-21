import logging

from ..remote_control.constants import SUCCESS_CODE
from ..remote_control.io_stream import IOStream
from ..remote_control.message_io import MessageIO
from ..remote_control.task import Task
from ..remote_control.task_manager import TaskManager

logger = logging.getLogger(__name__)


class RemoteControl:
    def __init__(self, device: IOStream):
        self._manager = TaskManager(MessageIO(device))

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
        pass
