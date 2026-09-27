import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from elasticai.experiment_framework.remote_control.serial_protocol_stream import (
    SerialTransportStream,
)


@pytest.mark.asyncio
async def test_write_and_read():
    stream = SerialTransportStream(on_lost=lambda exc: None)

    transport = AsyncMock(spec=asyncio.Transport)

    stream.connection_made(transport)

    await stream.write(b"ping")
    transport.write.assert_called_once_with(b"ping")

    stream.data_received(b"ping")
    assert await stream.read(4) == b"ping"


async def test_connection_lost():
    lost_event = asyncio.Event()

    def on_lost(exc):
        lost_event.set()

    stream = SerialTransportStream(on_lost=on_lost)

    transport = Mock()
    stream.connection_made(transport)
    stream.connection_lost(Exception())

    assert lost_event.is_set()
