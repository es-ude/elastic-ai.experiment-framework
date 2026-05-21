import pytest

from elasticai.experiment_framework.remote_control.pc_side.protocol.commands import (
    Command,
)
from elasticai.experiment_framework.remote_control.pc_side.protocol.constants import (
    HEADER_SIZE,
)
from elasticai.experiment_framework.remote_control.pc_side.protocol.flags import Flags
from elasticai.experiment_framework.remote_control.pc_side.protocol.header import Header
from elasticai.experiment_framework.remote_control.pc_side.protocol.message import (
    Message,
)


@pytest.fixture
def header():
    return Header(
        Command.ACK,
        Flags(need_ack=True, has_crc=False, is_last=False),
        transaction_id=100,
        payload_len=11,
    )


def test_empty_payload():
    msg = Message(
        Command.ACK,
        b"",
        flags=0,
        transaction_id=0,
    )

    data = msg.to_bytes()
    parsed = Message.from_bytes(data)

    assert parsed.payload == b""
    assert parsed.header.payload_len == 0


def test_to_bytes(header):
    payload = b"Hello world"

    msg = Message(
        header.command,
        payload,
        header.flags.to_byte(),
        header.transaction_id,
    )

    data = msg.to_bytes()

    assert data[:HEADER_SIZE] == header.to_bytes()
    assert data[HEADER_SIZE:] == payload
    
def test_from_bytes(header):
    payload = b"Hello world"
    data = header.to_bytes() + payload
    msg = Message.from_bytes(data)
    assert msg.header == header
    assert msg.payload == payload


def test_raises_exception_when_invalid_payload_length(header):

    raw = header.to_bytes() + b"TOO_LONG_PAYLOAD"

    with pytest.raises(Exception):
        Message.from_bytes(raw)


def test_message_round_trip():
    msg1 = Message(
        Command.ACK,
        b"Hello world",
        flags=0x01,
        transaction_id=42,
    )

    data = msg1.to_bytes()
    msg2 = Message.from_bytes(data)

    assert msg1 == msg2


def test_message_equality():
    m1 = Message(Command.ACK, b"abc", flags=1, transaction_id=7)
    m2 = Message(Command.ACK, b"abc", flags=1, transaction_id=7)

    assert m1 == m2
