from unittest.mock import AsyncMock, Mock

import pytest

from elasticai.experiment_framework.remote_control.commands import (
    Command,
)
from elasticai.experiment_framework.remote_control.task import (
    TaskState,
)


class FakeDevice:
    def __init__(self):
        self.connection = Mock()
        self.connection.send = AsyncMock(return_value=None)
        self._callbacks = {}

    def expect(self, tid, cb):
        self._callbacks[tid] = cb

    async def inject(self, tid: int, cmd: Command, payload: bytes = b""):
        cb = self._callbacks.get(tid)
        if cb is None:
            raise AssertionError(f"No callback for tid={tid}")

        msg = Mock()
        msg.header = Mock()
        msg.header.transaction_id = tid
        msg.header.command = cmd
        msg.header.flags = Mock(need_ack=False, is_last=False)
        msg.payload = payload

        await cb(msg)


@pytest.fixture
def device():
    return FakeDevice()


class TestBasic:
    @pytest.mark.asyncio
    async def test_open_task(self, controller, device):
        ctx = await controller.open_task(func_id=1)

        assert ctx.transaction_id is not None
        assert ctx.state == TaskState.OPENING

    @pytest.mark.asyncio
    async def test_send_and_receive_chunk(self, controller, device):
        ctx = await controller.open_task(func_id=1)

        await device.inject(ctx.transaction_id, Command.DATA_CHUNK, b"\x00hello")

        assert b"hello" in ctx.received_data

    @pytest.mark.asyncio
    async def test_finish_task(self, controller, device):
        ctx = await controller.open_task(func_id=1)

        await device.inject(ctx.transaction_id, Command.RETURN)

        assert ctx.state == TaskState.FINISHED
        assert ctx.transaction_id not in controller._tasks


class TestDataChunks:
    @pytest.mark.asyncio
    async def test_single_chunk(self, controller, device):
        ctx = await controller.open_task(func_id=1)

        await device.inject(ctx.transaction_id, Command.DATA_CHUNK, b"\x00data")

        assert ctx.received_data == b"data"

    @pytest.mark.asyncio
    async def test_multiple_chunks(self, controller, device):
        ctx = await controller.open_task(func_id=1)

        await device.inject(ctx.transaction_id, Command.DATA_CHUNK, b"\x00part1")
        await device.inject(ctx.transaction_id, Command.DATA_CHUNK, b"\x01part2")

        assert b"part1" in ctx.received_data
        assert b"part2" in ctx.received_data

    @pytest.mark.asyncio
    @pytest.mark.parametrize("size", [1, 10, 100, 1000])
    async def test_various_chunk_sizes(self, controller, device, size):
        ctx = await controller.open_task(func_id=1)
        data = b"x" * size

        await device.inject(ctx.transaction_id, Command.DATA_CHUNK, b"\x00" + data)

        assert len(ctx.received_data) >= size


class TestTransactionIds:
    @pytest.mark.asyncio
    async def test_unique_ids(self, controller):
        ctx1 = await controller.open_task(func_id=1)
        ctx2 = await controller.open_task(func_id=2)

        assert ctx1.transaction_id != ctx2.transaction_id

    @pytest.mark.asyncio
    async def test_sequential_ids(self, controller):
        ctx1 = await controller.open_task(func_id=1)
        ctx2 = await controller.open_task(func_id=2)

        assert ctx1.transaction_id < ctx2.transaction_id

    @pytest.mark.asyncio
    async def test_ids_reused_after_finish(self, controller, device):
        ctx1 = await controller.open_task(func_id=1)
        tid1 = ctx1.transaction_id

        await device.inject(tid1, Command.RETURN)

        ctx2 = await controller.open_task(func_id=2)
        tid2 = ctx2.transaction_id

        assert tid1 == tid2


class TestErrors:
    @pytest.mark.asyncio
    async def test_unknown_tid_raises(self, device):
        with pytest.raises(AssertionError):
            await device.inject(999, Command.RETURN)

    @pytest.mark.asyncio
    async def test_finish_without_data(self, controller, device):
        ctx = await controller.open_task(func_id=1)

        await device.inject(ctx.transaction_id, Command.RETURN)

        assert ctx.state == TaskState.FINISHED
        assert len(ctx.received_data) == 0


class TestIntegration:
    @pytest.mark.asyncio
    async def test_complete_task_no_data(self, controller, device):
        ctx = await controller.open_task(func_id=1)
        await device.inject(ctx.transaction_id, Command.RETURN)

        assert ctx.state == TaskState.FINISHED

    @pytest.mark.asyncio
    async def test_complete_task_with_data(self, controller, device):
        ctx = await controller.open_task(func_id=1)
        await device.inject(ctx.transaction_id, Command.DATA_CHUNK, b"\x00data")
        await device.inject(ctx.transaction_id, Command.RETURN)

        assert ctx.state == TaskState.FINISHED
        assert b"data" in ctx.received_data

    @pytest.mark.asyncio
    async def test_multiple_tasks_interleaved(self, controller, device):
        ctx1 = await controller.open_task(func_id=1)
        ctx2 = await controller.open_task(func_id=2)

        await device.inject(ctx1.transaction_id, Command.DATA_CHUNK, b"\x00data1")
        await device.inject(ctx2.transaction_id, Command.DATA_CHUNK, b"\x00data2")

        await device.inject(ctx1.transaction_id, Command.RETURN)
        await device.inject(ctx2.transaction_id, Command.RETURN)

        assert ctx1.state == TaskState.FINISHED
        assert ctx2.state == TaskState.FINISHED
        assert b"data1" in ctx1.received_data
        assert b"data2" in ctx2.received_data
