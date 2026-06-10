import asyncio
import logging
import socket
import subprocess
import time
from typing import AsyncGenerator

import pytest

from elasticai.experiment_framework.remote_control.callback_actions import (
    CallbackAction,
    CloseTask,
    SendChunk,
)
from elasticai.experiment_framework.remote_control.connection_provider import (
    ConnectionProvider,
)
from elasticai.experiment_framework.remote_control.message_io import (
    MessageIO,
)
from elasticai.experiment_framework.remote_control.task import (
    Task,
    TaskState,
)
from elasticai.experiment_framework.remote_control.task_manager import (
    TaskManager,
)

logging.basicConfig(format="%(message)s")
logger = logging.getLogger(__name__)


SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8080

SERVER_CMAKE = "example-firmwares/remote_control"


def wait_for_port(host, port, timeout=15.0):
    start = time.time()

    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=0.1):
                return True
        except OSError:
            time.sleep(0.05)

    return False


@pytest.fixture(scope="session", autouse=True)
def build_server():
    configure = subprocess.run(
        ["cmake", "--preset", "debug"],
        cwd=SERVER_CMAKE,
        capture_output=True,
        text=True,
    )

    if configure.returncode != 0:
        pytest.fail(f"CMake configure failed:\n{configure.stderr}")

    build = subprocess.run(
        ["cmake", "--build", "--preset", "debug", "--clean-first"],
        cwd=SERVER_CMAKE,
        capture_output=True,
        text=True,
    )

    if build.returncode != 0:
        pytest.fail(
            f"CMake build failed\n\nSTDOUT:\n{build.stdout}\n\nSTDERR:\n{build.stderr}"
        )


@pytest.fixture
def c_server(build_server):

    logger.info(
        f"Starting server: /build/debug/remote_control {SERVER_HOST} {SERVER_PORT}"
    )
    proc = subprocess.Popen(
        ["./build/debug/remote_control", SERVER_HOST, str(SERVER_PORT)],
        cwd=SERVER_CMAKE,
        text=True,
    )

    time.sleep(0.5)

    if proc.poll() is not None:
        out, err = proc.communicate(timeout=2)

        raise RuntimeError(
            f"Server crashed\n"
            f"exit code: {proc.returncode}\n"
            f"stdout:\n{out}\n"
            f"stderr:\n{err}\n"
        )

    if not wait_for_port(SERVER_HOST, SERVER_PORT):
        proc.kill()

        pytest.fail("Server failed to start")

    yield proc

    proc.terminate()

    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()


_logger = logging.getLogger(__name__)


class DummyTask(Task):
    def __init__(self, task_def_id: int, msg: bytes) -> None:
        self.msg = msg
        self.task_def_id = task_def_id
        self.need_ack = False
        super().__init__()

    async def on_opened(self) -> AsyncGenerator[CallbackAction, None]:
        _logger.debug(f"[CLIENT] callback: task openned state = {self.state}")
        yield SendChunk(self.msg)

    async def on_data_chunk_received(self) -> AsyncGenerator[CallbackAction, None]:
        _logger.debug(f"[CLIENT] callback: data chunk received{self.received_data} ")
        return
        yield

    async def on_return(self) -> AsyncGenerator[CallbackAction, None]:
        _logger.debug(f"[CLIENT] callback: task returned = {self.state}")
        return
        yield CloseTask(need_ack=True)


class TestClient:
    @pytest.mark.asyncio
    async def test_round_trip_message(self, c_server):
        data = b"abcdefghijkl"
        provider = ConnectionProvider()
        stream = await provider.connectTCP(SERVER_HOST, SERVER_PORT)
        device = MessageIO(stream)
        manager = TaskManager(device)
        await manager.start()
        task = DummyTask(task_def_id=0, msg=data)

        (task_openned,) = (await manager.open_task(task),)
        await task_openned._returned_event.wait()
        await manager.stop()

        assert task.state == TaskState.RETURNED
        assert task.received_data[0] == data

    @pytest.mark.asyncio
    async def test_adding_need_ack_waits_for_the_ack(self, c_server):
        data = b"abcdefghijkl"
        provider = ConnectionProvider()
        stream = await provider.connectTCP(SERVER_HOST, SERVER_PORT)
        device = MessageIO(stream)
        manager = TaskManager(device)
        await manager.start()
        task = DummyTask(task_def_id=0, msg=data)

        (task_openned,) = (await manager.open_task(task, need_ack=True),)
        await task_openned._opened_event.wait()
        await manager.stop()

        assert task.state == TaskState.OPENED
        assert task._opened_event.is_set()

    @pytest.mark.asyncio
    async def test_closing_task(self, c_server):
        data = b"abcdefghijkl"
        provider = ConnectionProvider()
        stream = await provider.connectTCP(SERVER_HOST, SERVER_PORT)
        device = MessageIO(stream)
        manager = TaskManager(device)
        await manager.start()
        task = DummyTask(task_def_id=0, msg=data)
        task.timeout = 8

        (task_openned,) = (await manager.open_task(task),)

        await asyncio.sleep(1)

        assert task.state == TaskState.RETURNED

        await manager.close_task(task_openned, need_ack=True)

        assert task.state == TaskState.CLOSED
