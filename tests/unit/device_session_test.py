from unittest.mock import AsyncMock, Mock

import pytest

from elasticai.experiment_framework.remote_control.pc_side.protocol.device_session import (
    DeviceSession,
)
from elasticai.experiment_framework.remote_control.pc_side.protocol.message import (
    Message,
)


def make_message(tid: int):
    msg = Mock(spec=Message)
    msg.header = Mock()
    msg.header.transaction_id = tid
    return msg


@pytest.mark.asyncio
async def test_expectation_callback_triggered():
    conn = Mock()
    conn.receive = AsyncMock()

    msg = make_message(42)
    conn.receive.side_effect = [msg, TimeoutError()]

    session = DeviceSession(1, {}, conn)

    callback = Mock()

    session.expect(42, callback)
    await session.start()

    callback.assert_called_once_with(msg)


@pytest.mark.asyncio
async def test_unhandled_message_logs(caplog):
    conn = Mock()
    conn.receive = AsyncMock()

    msg = make_message(99)
    conn.receive.side_effect = [msg, TimeoutError()]

    session = DeviceSession(1, {}, conn)

    await session.start()

    assert "unhandled message" in caplog.text


@pytest.mark.asyncio
async def test_multiple_expectations():
    conn = Mock()
    conn.receive = AsyncMock()

    msg1 = make_message(1)
    msg2 = make_message(2)

    conn.receive.side_effect = [msg1, msg2, TimeoutError()]

    session = DeviceSession(1, {}, conn)

    cb1 = AsyncMock()
    cb2 = AsyncMock()

    session.expect(1, cb1)
    session.expect(2, cb2)

    await session.start()

    cb1.assert_called_once_with(msg1)
    cb2.assert_called_once_with(msg2)


@pytest.mark.asyncio
async def test_stop_closes_connection():
    conn = Mock()
    conn.close = AsyncMock()

    session = DeviceSession(1, {}, conn)
    await session.start()

    await session.stop()

    conn.close.assert_called_once()


@pytest.mark.asyncio
async def test_receive_loop_breaks_on_error():
    conn = Mock()
    conn.receive = AsyncMock(side_effect=Exception("boom"))

    session = DeviceSession(1, {}, conn)

    await session.start()

    assert not session._running
    assert session._task.done()
