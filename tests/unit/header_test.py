import struct

import pytest

from elasticai.experiment_framework.remote_control.commands import (
    Command,
)
from elasticai.experiment_framework.remote_control.constants import (
    HEADER_FORMAT,
    HEADER_SIZE,
    SYNC_BYTE,
)
from elasticai.experiment_framework.remote_control.flags import Flags
from elasticai.experiment_framework.remote_control.header import Header


def test_to_bytes():
    h = Header(
        Command.ACK,
        Flags(need_ack=True, has_crc=False, is_last=False),
        transaction_id=100,
        payload_len=63,
    )

    data = h.to_bytes()

    assert len(data) == HEADER_SIZE
    assert data[0] == SYNC_BYTE
    assert data[1] == 0x5
    assert data[2] == 0x1
    assert data[3] == 0x64
    assert data[4] == 0x3F


def test_from_bytes():
    h_bytes = struct.pack(
        HEADER_FORMAT,
        SYNC_BYTE,
        Command.OPEN_TASK,
        Flags(need_ack=False, has_crc=True, is_last=True).to_byte(),
        0x10,
        0x11,
    )

    h = Header.from_bytes(h_bytes)

    assert h.command == Command.OPEN_TASK
    assert h.flags == Flags(False, True, True)
    assert h.transaction_id == 16
    assert h.payload_len == 17


def test_raise_exception_when_wrong_sync_bytes():
    h_bytes = struct.pack(
        HEADER_FORMAT,
        0xAB,
        Command.OPEN_TASK,
        Flags(need_ack=False, has_crc=True, is_last=True).to_byte(),
        0x10,
        0x11,
    )
    with pytest.raises(ValueError):
        Header.from_bytes(h_bytes)


def test_raise_exception_when_invalid_size():
    h_bytes = struct.pack(
        HEADER_FORMAT[:5],
        0xAB,
        Command.OPEN_TASK,
        Flags(need_ack=False, has_crc=True, is_last=True).to_byte(),
        0x10,
    )
    with pytest.raises(ValueError, match="too short"):
        Header.from_bytes(h_bytes)


def test_raise_exception_when_invalid_transaction_id():

    with pytest.raises(ValueError, match="transaction_id"):
        Header(
            Command.ACK,
            Flags(need_ack=True, has_crc=False, is_last=False),
            transaction_id=1578,
            payload_len=63,
        )


def test_raise_exception_when_invalid_payload_len():

    with pytest.raises(ValueError, match="payload_len"):
        Header(
            Command.ACK,
            Flags(need_ack=True, has_crc=False, is_last=False),
            transaction_id=14,
            payload_len=-1,
        )


@pytest.mark.parametrize(
    "command, flags, transaction_id, payload_len",
    [
        (Command.OPEN_TASK, 0x00, 0, 0),
        (Command.DATA_CHUNK, 0x01, 1, 100),
        (Command.ACK, 0x05, 255, 1000),
        (Command.RETURN, 0xFF, 128, 65535),
    ],
)
def test_to_bytes_from_bytes(command, flags, transaction_id, payload_len):
    h1 = Header(command, Flags.from_byte(flags), transaction_id, payload_len)
    data = h1.to_bytes()
    h2 = Header.from_bytes(data)

    assert h2.command == command
    assert h2.flags == Flags.from_byte(flags)
    assert h2.transaction_id == transaction_id
    assert h2.payload_len == payload_len
