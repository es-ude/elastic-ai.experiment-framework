import asyncio
from typing import AsyncGenerator, override

import pytest

from elasticai.experiment_framework.remote_control.callback_actions import (
    CallbackAction,
    NoAction,
    SendChunk,
)
from elasticai.experiment_framework.remote_control.commands import (
    Command,
)
from elasticai.experiment_framework.remote_control.exceptions import (
    InvalidChecksumError,
)
from elasticai.experiment_framework.remote_control.flags import Flags
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
        item = await self.tx.get()

        if isinstance(item, Exception):
            raise item

        return item

    async def write(self, msg: Message) -> None:
        self.rx.append(msg)


class DummyTask(Task):
    def __init__(self, task_def_id: int, msg: bytes) -> None:
        super().__init__(task_def_id)
        self.msg = msg
        self.need_ack = False

    @override
    async def on_opened(self) -> AsyncGenerator[CallbackAction, None]:
        yield NoAction()

    @override
    async def on_data_chunk_received(self) -> AsyncGenerator[CallbackAction, None]:
        yield NoAction()

    @override
    async def on_return(self) -> AsyncGenerator[CallbackAction, None]:
        yield NoAction()


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
    return Message(Command.RETURN, b"0", task_id=task1.task_id)


@pytest.fixture
def device():
    return DummyMessageIO()


@pytest.fixture
async def task_manager(device):
    manager = TaskManager(device, timeout=0.1)
    await manager.start()
    yield manager
    await manager.stop()


class TestOpenTask:
    async def test_open_task_sends_open_task(self, task_manager, task1):
        await task_manager.open_task(task1)

        assert task_manager._device.rx[0].header.command == Command.OPEN_TASK

    async def test_open_task_state(self, task_manager, task1):
        await task_manager.open_task(task1)

        assert task1.state == TaskState.OPENED

    async def test_open_task_callback(self, task_manager, msg):

        class OpenTask(DummyTask):
            @override
            async def on_opened(self):
                yield SendChunk(self.msg)

        task = OpenTask(task_def_id=0, msg=msg.encode())

        await task_manager.open_task(task)

        assert task_manager._device.rx[1].header.command == Command.DATA_CHUNK
        assert task_manager._device.rx[1].payload == msg.encode()

    async def test_open_task_with_ack_waits_for_ack(self, task_manager, task1, ack):

        open_task_co = asyncio.create_task(task_manager.open_task(task1, need_ack=True))

        await asyncio.sleep(0)
        assert task1.state == TaskState.OPENING

        await task_manager._device.tx.put(ack)

        await open_task_co

        assert task1.state == TaskState.OPENED


class TestDataChunks:
    async def test_receive_data_chunk(self, task_manager, task1, msg, data_chunk):
        await task_manager.open_task(task1)

        await task_manager._device.tx.put(
            data_chunk,
        )
        await asyncio.sleep(0)
        assert task1.state == TaskState.RECEIVED_DATA
        assert task1.received_data[0] == msg.encode()

    async def test_receive_multiple_chunks(self, task_manager, task1):
        await task_manager.open_task(task1)
        data_1 = b"hello"
        data_2 = b"world"

        await task_manager._device.tx.put(
            Message(Command.DATA_CHUNK, data_1, task_id=task1.task_id, msg_id=0x01)
        )
        await task_manager._device.tx.put(
            Message(Command.DATA_CHUNK, data_2, task_id=task1.task_id, msg_id=0x02)
        )
        await asyncio.sleep(0)

        assert task1.state == TaskState.RECEIVED_DATA
        assert task1.received_data[1] == data_1
        assert task1.received_data[2] == data_2

    async def test_send_chunk(self, task_manager, task1):
        await task_manager.open_task(task1)
        data = b"hello"
        next_msg_id = task1._next_msg_id
        await task_manager.send_chunk(task1, data)

        chunk = Message(Command.DATA_CHUNK, payload=data, task_id=0, msg_id=next_msg_id)

        assert task_manager._device.rx[next_msg_id] == chunk

    async def test_received_ack_of_data_chunks(self, task_manager, task1):
        await task_manager.open_task(task1)
        data = b"hello"

        chunk_msg_id = task1._next_msg_id

        task_coro = asyncio.create_task(
            task_manager.send_chunk(task1, data, need_ack=True)
        )

        ack = Message(
            Command.ACK,
            payload=b"",
            task_id=task1.task_id,
            msg_id=chunk_msg_id,
        )

        await asyncio.sleep(0)

        assert task1._pending_acks[chunk_msg_id] is not None

        await task_manager._device.tx.put(ack)
        await task_coro

        assert task1._pending_acks.get(chunk_msg_id, None) is None

    async def test_ack_when_received_data_chunks(self, task_manager, task1):
        await task_manager.open_task(task1)
        data = b"hello"

        chunk_msg_id = 2
        chunk = Message(
            Command.DATA_CHUNK,
            payload=data,
            flags=Flags(need_ack=True).to_number(),
            task_id=task1.task_id,
            msg_id=chunk_msg_id,
        )

        ack = Message(
            Command.ACK,
            payload=b"",
            task_id=task1.task_id,
            msg_id=chunk_msg_id,
        )
        await asyncio.sleep(0)

        await task_manager._device.tx.put(chunk)
        await asyncio.sleep(0)

        assert task_manager._device.rx[1] == ack


class TestReturn:
    async def test_return_mark_task_as_finished(self, task_manager, task1, ret):
        await task_manager.open_task(task1)

        await task_manager._device.tx.put(ret)

        await asyncio.sleep(0)

        assert task1.state == TaskState.RETURNED


class TestCloseTask:
    async def test_close_mark_task_as_closed(self, task_manager, task1):
        await task_manager.open_task(task1)

        await task_manager.close_task(task1)

        assert task1.state == TaskState.CLOSED

    async def test_closed_with_ack_waits_ack(self, task_manager, task1):
        await task_manager.open_task(task1)

        close_task_msg_id = task1._next_msg_id

        close_task_coro = asyncio.create_task(
            task_manager.close_task(task1, need_ack=True)
        )
        await asyncio.sleep(0)

        ack = Message(
            Command.ACK, payload=b"", task_id=task1.task_id, msg_id=close_task_msg_id
        )

        await task_manager._device.tx.put(ack)
        await asyncio.sleep(0)

        await close_task_coro

        assert task1.state == TaskState.CLOSED

    async def test_close_state_transitions(self, task_manager, task1, ack):
        await task_manager.open_task(task1)

        close_task_msg_id = task1._next_msg_id
        ack = Message(
            Command.ACK, payload=b"", task_id=task1.task_id, msg_id=close_task_msg_id
        )

        async def send_ack_delayed():
            await asyncio.sleep(0.01)
            await task_manager._device.tx.put(ack)

        asyncio.create_task(send_ack_delayed())

        close_task_coro = asyncio.create_task(
            task_manager.close_task(task1, need_ack=True)
        )

        await asyncio.sleep(0)

        assert task1.state == TaskState.CLOSING

        await close_task_coro

        assert task1.state == TaskState.CLOSED
        assert task1.task_id not in task_manager._running_tasks


class TestTaskIds:
    async def test_unique_ids(self, task_manager, task1, task2):

        await task_manager.open_task(task1)
        await task_manager.open_task(task2)

        assert task2.task_id != task1.task_id

    async def test_sequential_ids(self, task_manager, task1, task2):
        await task_manager.open_task(task1)
        await task_manager.open_task(task2)

        assert task1.task_id < task2.task_id

    async def test_ids_reused_after_task_closed(self, task_manager, task1, task2):
        await task_manager.open_task(task1)
        task_id1 = task1.task_id

        await task_manager.close_task(task1)
        await asyncio.sleep(0)

        await task_manager.open_task(task2)
        task_id2 = task2.task_id

        assert task_id1 == task_id2


class TestMessageRetransmission:
    async def test_retransmission_after_timeout(self, task_manager, task1):
        open_task_msg_id = task1._next_msg_id
        open_task_future = asyncio.create_task(
            task_manager.open_task(task1, need_ack=True)
        )

        while len(task_manager._device.rx) < 3:
            await asyncio.sleep(0)

        ack = Message(
            Command.ACK,
            payload=b"",
            task_id=task1.task_id,
            msg_id=open_task_msg_id,
        )

        await task_manager._device.tx.put(ack)

        await open_task_future

        assert len(task_manager._device.rx) == 3


class TestChecksum:
    async def test_sends_an_ack_when_invalid_checksum_and_ack(
        self, task_manager, task1
    ):
        await task_manager.open_task(task1)

        invalid_chunk_msg_id = 0x1

        invalid_chunk = Message(
            Command.DATA_CHUNK,
            payload=b"hello",
            flags=Flags(need_ack=True, has_crc=True).to_number(),
            task_id=task1.task_id,
            msg_id=invalid_chunk_msg_id,
        )

        await task_manager._device.tx.put(InvalidChecksumError(invalid_chunk))

        await asyncio.sleep(0)

        nack = Message(
            Command.NACK,
            payload=b"",
            task_id=task1.task_id,
            msg_id=invalid_chunk_msg_id,
        )

        assert task_manager._device.rx[1] == nack
