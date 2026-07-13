import pytest
from crc import Calculator, Crc8

from elasticai.experiment_framework.remote_control.commands import (
    Command,
)
from elasticai.experiment_framework.remote_control.constants import (
    HEADER_SIZE,
    NUM_BYTES_CHECKSUM,
)
from elasticai.experiment_framework.remote_control.exceptions import (
    InvalidChecksumError,
)
from elasticai.experiment_framework.remote_control.flags import Flags
from elasticai.experiment_framework.remote_control.header import Header
from elasticai.experiment_framework.remote_control.message import (
    Message,
)

_calculator = Calculator(Crc8.CCITT.value)


@pytest.fixture
def header():
    return Header(
        Command.ACK,
        Flags(need_ack=True, has_crc=False),
        task_id=100,
        msg_id=45,
        payload_len=11,
    )


def test_empty_payload():
    msg = Message(
        Command.ACK,
        b"",
        flags=0,
        task_id=0,
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
        header.flags.to_number(),
        header.task_id,
        header.msg_id,
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


def test_checksum_verify():
    data = b"Hello world"
    message = Message(
        command=Command.OPEN_TASK,
        payload=data,
        flags=Flags(has_crc=True).to_number(),
    )
    header = message.header.to_bytes()
    payload = message.payload

    assert _calculator.verify(header + payload, message.checksum)


def test_to_bytes_contains_checksum():
    data = b"Hello world"
    message = Message(
        command=Command.OPEN_TASK,
        payload=data,
        flags=Flags(has_crc=True).to_number(),
    )
    header = message.header.to_bytes()
    payload = message.payload
    crc = _calculator.checksum(header + payload)

    assert message.to_bytes() == header + payload + int.to_bytes(
        crc, NUM_BYTES_CHECKSUM
    )


def test_checksum():
    data = b"Hello world"
    message = Message(
        command=Command.OPEN_TASK,
        payload=data,
        flags=Flags(has_crc=True).to_number(),
    )
    header = message.header.to_bytes()
    payload = message.payload
    crc = _calculator.checksum(header + payload)

    from_bytes_message = Message.from_bytes(
        header + payload + int.to_bytes(crc, NUM_BYTES_CHECKSUM)
    )

    assert from_bytes_message.checksum == crc


def test_from_bytes_raises_exception_when_invalid_checksum():
    data = b"Hello world"
    message = Message(
        command=Command.OPEN_TASK,
        payload=data,
        flags=Flags(has_crc=True).to_number(),
    )
    header = message.header.to_bytes()
    payload = message.payload

    invalid_message = header + payload + b"\0x0"

    with pytest.raises(InvalidChecksumError):
        message.from_bytes(invalid_message)


def test_raises_exception_when_invalid_payload_length(header):

    raw = header.to_bytes() + b"TOO_LONG_PAYLOAD"

    with pytest.raises(Exception):
        Message.from_bytes(raw)


def test_message_round_trip():
    msg1 = Message(
        Command.ACK,
        b"Hello world",
        flags=0x01,
        task_id=42,
    )

    data = msg1.to_bytes()
    msg2 = Message.from_bytes(data)

    assert msg1 == msg2


def test_message_equality():
    m1 = Message(Command.ACK, b"abc", flags=1, task_id=7)
    m2 = Message(Command.ACK, b"abc", flags=1, task_id=7)

    assert m1 == m2
