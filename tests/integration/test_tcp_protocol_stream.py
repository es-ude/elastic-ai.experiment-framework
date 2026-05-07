import asyncio

import pytest

from elasticai.experiment_framework.remote_control.connection_provider import (
    ConnectionProvider,
)
from elasticai.experiment_framework.remote_control.tcp_protocol_stream import (
    TCPProtocolStream,
)


@pytest.fixture
async def tcp_server():
    async def echo(reader, writer):
        data = await reader.read(1024)
        writer.write(data)
        await writer.drain()
        writer.close()

    server = await asyncio.start_server(echo, "127.0.0.1", port=0)
    addr = server.sockets[0].getsockname()
    yield addr
    server.close()
    await server.wait_closed()


async def test_write_and_read(tcp_server):
    host, port = tcp_server
    provider = ConnectionProvider()
    stream = await provider.connectTCP(host, port)

    data = b"Hello World"
    await stream.write(data)
    result = await stream.read(len(data))

    assert result == data


async def test_connection_lost(tcp_server):
    host, port = tcp_server

    lost_event = asyncio.Event()

    def on_lost(exc):
        return lost_event.set()

    loop = asyncio.get_running_loop()
    _, stream = await loop.create_connection(
        lambda: TCPProtocolStream(on_lost), host, port
    )

    await stream.write(b"ping")
    await stream.read(4)

    await asyncio.wait_for(lost_event.wait(), timeout=1.0)

    assert lost_event.is_set()
