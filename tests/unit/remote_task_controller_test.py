from unittest.mock import AsyncMock, Mock, patch

import pytest

from elasticai.experiment_framework.remote_control.pc_side.protocol.device_session import (
    DeviceSession,
)
from elasticai.experiment_framework.remote_control.pc_side.protocol.remote_control_protocol import (
    ConnectionProvider,
)


@pytest.fixture
def mocked_connection():
    conn = Mock()
    conn.connect = AsyncMock()
    conn.close = AsyncMock()

    with patch(
        "elasticai.experiment_framework.remote_control.pc_side.protocol.remote_control_protocol.Connection",
        return_value=conn,
    ):
        yield conn


@pytest.mark.asyncio
async def test_connect_tcp_creates_session(mocked_connection):
    protocol = ConnectionProvider()

    with patch.object(DeviceSession, "start", new=AsyncMock()):
        session = await protocol.connect_tcp("localhost", 1234)

    assert len(protocol._sessions) == 1
    assert session.id == 0
    assert session.device_info == {"host": "localhost", "port": "1234"}

    mocked_connection.connect.assert_called_once()


@pytest.mark.asyncio
async def test_duplicate_device_raises(mocked_connection):
    protocol = ConnectionProvider()

    with patch.object(DeviceSession, "start", new=AsyncMock()):
        await protocol.connect_tcp("localhost", 1234)

    with pytest.raises(Exception):
        await protocol.connect_tcp("localhost", 1234)


@pytest.mark.asyncio
async def test_disconnect_removes_session(mocked_connection):
    protocol = ConnectionProvider()

    with patch(
        "elasticai.experiment_framework.remote_control.pc_side.protocol.remote_control_protocol.Connection"
    ) as ConnMock:
        conn = Mock()
        conn.connect = AsyncMock()
        ConnMock.return_value = conn

        with patch.object(DeviceSession, "start", new=AsyncMock()):
            session = await protocol.connect_tcp("localhost", 1234)

        session.stop = AsyncMock()

        await protocol.disconnect(session)

    assert len(protocol._sessions) == 0
    session.stop.assert_called_once()


@pytest.mark.asyncio
async def test_max_devices_reached(mocked_connection):
    protocol = ConnectionProvider(max_devices=1)

    with patch(
        "elasticai.experiment_framework.remote_control.pc_side.protocol.remote_control_protocol.Connection"
    ) as ConnMock:
        conn = Mock()
        conn.connect = AsyncMock()
        ConnMock.return_value = conn

        with patch.object(DeviceSession, "start", new=AsyncMock()):
            await protocol.connect_tcp("localhost", 1234)

        with pytest.raises(RuntimeError):
            await protocol.connect_tcp("localhost", 9999)


@pytest.mark.asyncio
async def test_find_by_id(mocked_connection):
    protocol = ConnectionProvider()

    with patch.object(DeviceSession, "start", new=AsyncMock()):
        session = await protocol.connect_tcp("localhost", 1234)

    found = protocol.find_by_id(session.id)

    assert found == session


def test_find_by_id_returns_none():
    protocol = ConnectionProvider()

    result = protocol.find_by_id(999)

    assert result is None


@pytest.mark.asyncio
async def test_find_by_info(mocked_connection):
    protocol = ConnectionProvider()

    with patch.object(DeviceSession, "start", new=AsyncMock()):
        session = await protocol.connect_tcp("localhost", 1234)

    found = protocol.find_by_info({"host": "localhost", "port": "1234"})

    assert found == session


def test_find_by_info_raises():
    protocol = ConnectionProvider()

    with pytest.raises(Exception):
        protocol.find_by_info({"host": "missing", "port": "1"})


@pytest.mark.asyncio
async def test_connection_failure_closes_connection(mocked_connection):
    protocol = ConnectionProvider()
    mocked_connection.connect = AsyncMock(side_effect=Exception("boom"))
    with pytest.raises(Exception):
        await protocol.connect_tcp("localhost", 1234)

    mocked_connection.close.assert_called_once()
