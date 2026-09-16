import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from elasticai.experiment_framework.remote_control.connection_provider import (
    ConnectionProvider,
)
from elasticai.experiment_framework.remote_control.io_stream import IOStream


@pytest.fixture
async def tcp_server():
    async def handle(reader, writer):
        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(
        handle,
        host="127.0.0.1",
        port=0,
    )
    addr = server.sockets[0].getsockname()
    yield addr
    server.close()
    await server.wait_closed()


class TestTCPConnection:
    async def test_connect_success(self, tcp_server):
        host, port = tcp_server
        provider = ConnectionProvider()
        async with provider.connectTCP(host, port) as stream:
            assert stream is not None

    async def test_retries_on_failure(self):
        call_count = 0

        async def failing_then_succeeding(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionRefusedError("not ready yet")
            return (None, MagicMock())

        with patch(
            "elasticai.experiment_framework.remote_control.connection_provider.asyncio.get_running_loop"
        ) as mock_loop:
            mock_loop.return_value.create_connection = failing_then_succeeding

            provider = ConnectionProvider(max_trials=5)
            async with provider.connectTCP("host", 12):
                pass

        assert call_count == 3


class TestSerialConnection:
    def setup_method(self) -> None:

        self.port = "/dev/ttyACM0"
        self.baudrate = 115200

    @pytest.mark.hardware
    async def test_connect_success(self):

        provider = ConnectionProvider()
        async with provider.connectSerial(self.port, self.baudrate) as stream:
            assert stream is not None
            assert isinstance(stream, IOStream)

    async def test_retries_on_failure(self):
        with patch(
            "elasticai.experiment_framework.remote_control.connection_provider.serial_asyncio"
        ) as mock_serial_asyncio:
            mock_serial_asyncio.create_serial_connection = AsyncMock(
                side_effect=[
                    ConnectionRefusedError("not ready yet"),
                    ConnectionRefusedError("not ready yet"),
                    (None, MagicMock()),
                ]
            )

            provider = ConnectionProvider(max_trials=5)
            async with provider.connectSerial(self.port, self.baudrate):
                ...

        assert mock_serial_asyncio.create_serial_connection.call_count == 3
