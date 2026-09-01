import pytest

from elasticai.experiment_framework.remote_control.commands import Command
from elasticai.experiment_framework.remote_control.exceptions import (
    InvalidCommandPayloadError,
)
from elasticai.experiment_framework.remote_control.flags import Flags
from elasticai.experiment_framework.remote_control.io_stream import IOStream
from elasticai.experiment_framework.remote_control.message import Message
from elasticai.experiment_framework.remote_control.message_io import (
    MessageIO,
)


class DummyIO(IOStream):
    def __init__(self):
        self.tx = bytearray()
        self.current_read_pos = 0
        self.rx = bytearray()

    async def read(self, num_bytes: int) -> bytes | bytearray:
        old_pos = self.current_read_pos
        self.current_read_pos += num_bytes
        v = self.tx[old_pos : self.current_read_pos]
        return v

    async def write(self, data: bytes | bytearray) -> int:
        self.rx.extend(data)
        return len(data)


@pytest.fixture
def msg():
    return "Hello World"


@pytest.fixture
def data_chunk(msg):
    return Message(Command.DATA_CHUNK, msg.encode())


@pytest.fixture
def ack():
    return Message(Command.ACK, b"")


@pytest.fixture
def ret():
    return Message(Command.RETURN, b"0")


@pytest.fixture
def message_io():
    return MessageIO(DummyIO())


class TestBasic:
    @pytest.mark.asyncio
    async def test_read_message_frame(self, message_io, data_chunk):

        message_io._stream.tx.extend(data_chunk.to_bytes())
        msg = await message_io.read()

        assert msg == data_chunk

    @pytest.mark.asyncio
    async def test_write_message(self, message_io, ret):
        await message_io.write(ret)

        assert message_io._stream.rx == ret.to_bytes()

    @pytest.mark.asyncio
    async def test_round_trip(self, message_io, data_chunk):
        await message_io.write(data_chunk)
        message_io._stream.tx.extend(message_io._stream.rx)
        msg = await message_io.read()
        assert msg == data_chunk

    @pytest.mark.asyncio
    async def test_read_message_with_checksum(self, message_io):
        expected = Message(
            Command.DATA_CHUNK,
            b"payload",
            flags=Flags(has_crc=True).to_number(),
        )
        message_io._stream.tx.extend(expected.to_bytes())

        actual = await message_io.read()

        assert actual == expected

    @pytest.mark.asyncio
    async def test_preserves_command_payload_error(self, message_io):
        invalid_ack = Message(Command.ACK, b"unexpected")
        message_io._stream.tx.extend(invalid_ack.to_bytes())

        with pytest.raises(InvalidCommandPayloadError) as exc_info:
            await message_io.read()

        assert exc_info.value.message == invalid_ack
