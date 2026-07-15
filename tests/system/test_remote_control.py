import asyncio
import logging
import os
import signal
import socket
import subprocess
import time
from typing import AsyncGenerator
from unittest.mock import AsyncMock, PropertyMock, patch

import pytest
import pytest_asyncio

from elasticai.experiment_framework.remote_control.callback_actions import (
    CallbackAction,
    NoAction,
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
_logger = logging.getLogger(__name__)


SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8080

SERVER_CMAKE = "example-firmwares/remote_control"


def wait_for_port(host, port, timeout=10.0):
    start = time.time()

    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=0.1):
                return True
        except OSError:
            time.sleep(0.05)

    return False


@pytest.fixture(scope="session", autouse=False)
def build_server():
    configure = subprocess.run(
        ["cmake", "--preset", "host-debug"],
        cwd=SERVER_CMAKE,
        capture_output=True,
        text=True,
    )

    if configure.returncode != 0:
        pytest.fail(f"CMake configure failed:\n{configure.stderr}")

    build = subprocess.run(
        ["cmake", "--build", "--preset", "host-debug", "--clean-first"],
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

    _logger.info(
        f"""Starting server: /build/host-debug/src/app/remote_control 
        {SERVER_HOST} 
        {SERVER_PORT}"""
    )
    proc = subprocess.Popen(
        ["./build/host-debug/src/app/remote_control", SERVER_HOST, str(SERVER_PORT)],
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

    time.sleep(0.5)
    _logger.info(f"SERVER PID={proc.pid}")

    yield proc
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()


@pytest_asyncio.fixture()
async def manager(c_server):

    provider = ConnectionProvider()
    async with provider.connectTCP(SERVER_HOST, SERVER_PORT) as stream:
        manager = TaskManager(MessageIO(stream))

        await manager.start()
        try:
            yield manager
        finally:
            try:
                await manager.stop()
            finally:
                pass


class DummyTask(Task):
    def __init__(self, task_def_id: int, msg: bytes) -> None:
        super().__init__(task_def_id)
        self.msg = msg
        self.need_ack = False

    async def on_opened(self) -> AsyncGenerator[CallbackAction, None]:
        _logger.debug(f"[CLIENT] callback: task openned state = {self.state}")
        yield NoAction()

    async def on_data_chunk_received(self) -> AsyncGenerator[CallbackAction, None]:
        _logger.debug(f"[CLIENT] callback: data chunk received{self.received_data} ")
        yield NoAction()

    async def on_return(self) -> AsyncGenerator[CallbackAction, None]:
        _logger.debug(f"[CLIENT] callback: task returned = {self.state}")
        yield NoAction()


class TestTCPClient:
    @pytest.mark.asyncio
    async def test_round_trip_message(self, manager):
        data = b"abcdefghijkl"

        task = DummyTask(task_def_id=0, msg=data)

        await manager.open_task(task)
        await manager.send_chunk(task, data)
        await task.wait_for_return()

        assert task.state == TaskState.RETURNED
        assert task.received_data[0] == data

    @pytest.mark.asyncio
    async def test_adding_need_ack_waits_for_the_ack(self, manager):
        data = b"abcdefghijkl"

        task = DummyTask(task_def_id=0, msg=data)

        ack_received = asyncio.Event()

        original = manager._handle_ack

        async def delayed_ack(*args, **kwargs):
            ack_received.set()
            await asyncio.sleep(0.5)
            await original(*args, **kwargs)

        mock = AsyncMock(wraps=delayed_ack)
        setattr(manager, "_handle_ack", mock)

        task_open = asyncio.create_task(manager.open_task(task, need_ack=True))

        await ack_received.wait()

        assert task.state == TaskState.OPENING

        await task_open

        assert task.state == TaskState.OPENED

    @pytest.mark.asyncio
    async def test_closing_task(self, manager):
        data = b"abcdefghijkl"

        task = DummyTask(task_def_id=0, msg=data)
        task.timeout = 0.1

        await manager.open_task(task)
        await manager.send_chunk(task, data)

        await asyncio.sleep(1)

        assert task.state == TaskState.RETURNED

        await manager.close_task(task, need_ack=True)

        assert task.state == TaskState.CLOSED

    @pytest.mark.asyncio
    async def test_remote_retransmits_after_timeout_on_acks(self, manager, monkeypatch):
        data = b"abcdefghijkl"
        task = DummyTask(task_def_id=2, msg=data)
        task.timeout = 0.1

        count = 3

        async def ignore_twice_before_ack(task, message):
            nonlocal count
            count -= 1

            if count == 0:
                await manager._send_ack(message)

        monkeypatch.setattr(manager, "_handle_chunk", ignore_twice_before_ack)

        await manager.open_task(task)
        await manager.send_chunk(task, data)

        await asyncio.sleep(2)
        assert count == 0

    @pytest.mark.asyncio
    async def test_checksum_are_stripped(self, manager):
        data = b"abcdefghijkl"

        task = DummyTask(task_def_id=0, msg=data)
        task.has_crx = True
        task.timeout = 0.1

        await manager.open_task(task)
        await manager.send_chunk(task, data)
        
        await asyncio.sleep(0.1)

        assert task.state == TaskState.RETURNED
        assert task.received_data[0] == data

    @pytest.mark.asyncio
    async def test_wrong_checksum_send_nack_if_need_ack(self, manager):
        data = b"abcdefghijkl"

        task = DummyTask(task_def_id=0, msg=data)
        task.has_crx = True
        task.timeout = 0.5

        with patch(
            "elasticai.experiment_framework.remote_control.message.Message.checksum",
            new_callable=PropertyMock,
        ) as checksum_mock:
            checksum_mock.return_value = 0

            original = manager._handle_nack

            manager._handle_nack = AsyncMock(wraps=original)

            open_task_coro = asyncio.create_task(manager.open_task(task, need_ack=True))
            await asyncio.sleep(0.1)

            await open_task_coro

            manager._handle_nack.assert_called()
