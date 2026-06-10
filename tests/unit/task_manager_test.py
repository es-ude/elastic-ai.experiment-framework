import asyncio
from typing import AsyncGenerator, override

import pytest

from elasticai.experiment_framework.remote_control.callback_actions import (
    CallbackAction,
    SendChunk,
)
from elasticai.experiment_framework.remote_control.commands import (
    Command,
)
from elasticai.experiment_framework.remote_control.message import Message
from elasticai.experiment_framework.remote_control.task import (
    Task,
    TaskState,
)
from elasticai.experiment_framework.remote_control.task_manager import (
    TaskManager,
)


class DummyMessageIO:
    def __init__(self):
        self.tx: asyncio.Queue[Message] = asyncio.Queue()
        self.rx: list[Message] = []

    async def read(self) -> Message:
        return await self.tx.get()

    async def write(self, msg: Message) -> None:
        self.rx.append(msg)


class DummyTask(Task):
    def __init__(self, func_id: int, msg: bytes) -> None:
        super().__init__()
        self.msg = msg
        self.func_id = func_id
        self.need_ack = False

    @override
    async def on_opened(self):
        yield SendChunk(self.msg)

    @override
    async def on_data_chunk_received(self) -> AsyncGenerator[CallbackAction, None]:
        return
        yield

    @override
    async def on_return(self) -> AsyncGenerator[CallbackAction, None]:
        return
        yield


@pytest.fixture()
def msg():
    return "Hello World"


@pytest.fixture
def task1(msg):
    return DummyTask(1, msg.encode())


@pytest.fixture
def task2(msg):
    return DummyTask(0, msg=msg.encode())


@pytest.fixture
def data_chunk(msg):
    return Message(Command.DATA_CHUNK, msg.encode())


@pytest.fixture
def ack():
    return Message(Command.ACK, b"")


@pytest.fixture
def ret(task1):
    return Message(Command.RETURN, b"0", transaction_id=task1.transaction_id)


@pytest.fixture
def device():
    return DummyMessageIO()


@pytest.fixture
async def task_manager(device):
    manager = TaskManager(device)
    await manager.start()
    yield manager
    await manager.stop()


class TestOpenTask:
    async def test_open_task_sends_open_task(self, task_manager, task1):
        await task_manager.open_task(task1)

        assert task_manager._device.rx[0].header.command == Command.OPEN_TASK

    async def test_open_task_state(self, task_manager, task1):
        task1 = await task_manager.open_task(task1)
        assert task1.transaction_id is not None
        assert task1.state == TaskState.OPENED

    async def test_open_task_callback(self, task_manager, task1, msg):
        task1 = await task_manager.open_task(task1)

        assert task_manager._device.rx[1].header.command == Command.DATA_CHUNK
        assert task_manager._device.rx[1].payload[1:] == msg.encode()


class TestDataChunks:
    async def test_receive_data_chunk(self, task_manager, task1, msg):
        task1 = await task_manager.open_task(task1)
        data_id = b"\x00"

        await task_manager._device.tx.put(
            Message(
                Command.DATA_CHUNK,
                data_id + msg.encode(),
                transaction_id=task1.transaction_id,
            )
        )
        await asyncio.sleep(0)
        assert task1.state == TaskState.RECEIVED_DATA
        assert task1.received_data[0] == msg.encode()

    async def test_receive_multiple_chunks(self, task_manager, task1, msg):
        task1 = await task_manager.open_task(task1)
        data_1 = b"hello"
        data_2 = b"world"

        await task_manager._device.tx.put(
            Message(
                Command.DATA_CHUNK,
                b"\x01" + data_1,
                transaction_id=task1.transaction_id,
            )
        )
        await task_manager._device.tx.put(
            Message(
                Command.DATA_CHUNK,
                b"\x02" + data_2,
                transaction_id=task1.transaction_id,
            )
        )
        await asyncio.sleep(0)

        assert task1.state == TaskState.RECEIVED_DATA
        assert task1.received_data[1] == data_1
        assert task1.received_data[2] == data_2


class TestReturn:
    async def test_return_mark_task_as_finished(self, task_manager, task1, ret):
        await task_manager.open_task(task1)

        await task_manager._device.tx.put(ret)

        await asyncio.sleep(0)

        assert task1.state == TaskState.RETURNED


class TestTransactionIds:
    async def test_unique_ids(self, task_manager, task1, task2):

        await task_manager.open_task(task1)
        await task_manager.open_task(task2)

        assert task2.transaction_id != task1.transaction_id

    async def test_sequential_ids(self, task_manager, task1, task2):
        task1 = await task_manager.open_task(task1)
        task2 = await task_manager.open_task(task2)

        assert task1.transaction_id < task2.transaction_id

    async def test_ids_reused_after_finish(self, task_manager, task1, ret):
        task1 = await task_manager.open_task(task1)
        tid1 = task1.transaction_id

        await task_manager._device.tx.put(ret)
        await asyncio.sleep(0)

        task2 = await task_manager.open_task(task1)
        tid2 = task2.transaction_id

        assert tid1 == tid2
