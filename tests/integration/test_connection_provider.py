import asyncio
from unittest.mock import MagicMock, patch

import pytest

from elasticai.experiment_framework.remote_control.connection_provider import (
    ConnectionProvider,
)


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


async def test_connect_success(tcp_server):
    host, port = tcp_server
    provider = ConnectionProvider()
    stream = await provider.connectTCP(host, port)
    assert stream is not None


async def test_retries_on_failure():
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
        await provider.connectTCP("localhost", 1234)

    assert call_count == 3
