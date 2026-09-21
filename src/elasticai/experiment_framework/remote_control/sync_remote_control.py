import asyncio

from elasticai.experiment_framework.remote_control.constants import SUCCESS_CODE
from elasticai.experiment_framework.remote_control.io_stream import IOStream
from elasticai.experiment_framework.remote_control.message_io import MessageIO
from elasticai.experiment_framework.remote_control.task import Task
from elasticai.experiment_framework.remote_control.task_manager import TaskManager


class SyncRemoteControl:
    def __init__(self, device: IOStream):
        self._manager = TaskManager(MessageIO(device))
        self._loop = asyncio.get_event_loop()

    def __enter__(self):
        self._loop.run_until_complete(self._manager.start())
        self._initialize()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._loop.run_until_complete(self._manager.stop())

    def _run_task(self, task: Task):
        self._loop.run_until_complete(self._manager.open_task(task))

        try:
            return_code = self._loop.run_until_complete(task.wait_for_return())

            if return_code != SUCCESS_CODE:
                raise RuntimeError(
                    f"Remote task {task.task_id} failed with code {return_code}"
                )

            return return_code
        finally:
            self._loop.run_until_complete(self._manager.close_task(task))

    def _initialize(self):
        pass
