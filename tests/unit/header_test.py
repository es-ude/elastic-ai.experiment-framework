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
from elasticai.experiment_framework.remote_control.exceptions import (
    InvalidHeaderError,
    InvalidMsgIdError,
    InvalidPayloadLenError,
    InvalidTaskIdError,
)
from elasticai.experiment_framework.remote_control.flags import Flags
from elasticai.experiment_framework.remote_control.header import Header


def test_to_bytes():
    h = Header(
        Command.ACK,
        Flags(need_ack=True, has_crc=False),
        task_id=100,
        msg_id=1,
        payload_len=63,
    )

    data = h.to_bytes()

    expected = struct.pack(
        HEADER_FORMAT,
        SYNC_BYTE,
        Command.ACK,
        Flags(need_ack=True, has_crc=False).to_byte(),
        100,
        1,
        63,
    )
    assert data == expected
    assert len(data) == HEADER_SIZE


def test_from_bytes():
    h_bytes = struct.pack(
        HEADER_FORMAT,
        SYNC_BYTE,
        Command.OPEN_TASK,
        Flags(need_ack=False, has_crc=True).to_byte(),
        0x10,
        0x12,
        0x11,
    )

    h = Header.from_bytes(h_bytes)

    assert h.command == Command.OPEN_TASK
    assert h.flags == Flags(False, True)
    assert h.task_id == 16
    assert h.payload_len == 17


def test_raise_exception_when_wrong_sync_bytes():
    h_bytes = struct.pack(
        HEADER_FORMAT,
        0xAB,
        Command.OPEN_TASK,
        Flags(need_ack=False, has_crc=True).to_byte(),
        0x00,
        0x10,
        0x11,
    )
    with pytest.raises(InvalidHeaderError):
        Header.from_bytes(h_bytes)


def test_raise_exception_when_invalid_size():
    h_bytes = struct.pack(
        HEADER_FORMAT[:6],
        0xAB,
        Command.OPEN_TASK,
        Flags(need_ack=False, has_crc=True).to_byte(),
        0x93,
        0x10,
    )
    with pytest.raises(InvalidHeaderError, match="size"):
        Header.from_bytes(h_bytes)


def test_raise_exception_when_invalid_task_id():

    with pytest.raises(InvalidTaskIdError):
        Header(
            Command.ACK,
            Flags(need_ack=True, has_crc=False),
            task_id=1578,
            msg_id=1,
            payload_len=63,
        )


def test_raise_exception_when_invalid_msg_id():

    with pytest.raises(InvalidMsgIdError):
        Header(
            Command.ACK,
            Flags(need_ack=True, has_crc=False),
            task_id=1,
            msg_id=1578,
            payload_len=63,
        )


def test_raise_exception_when_invalid_payload_len():

    with pytest.raises(InvalidPayloadLenError):
        Header(
            Command.ACK,
            Flags(need_ack=True, has_crc=False),
            task_id=14,
            msg_id=1,
            payload_len=-1,
        )


@pytest.mark.parametrize(
    "command, flags, task_id, msg_id, payload_len",
    [
        (Command.OPEN_TASK, 0x00, 0, 0, 0),
        (Command.DATA_CHUNK, 0x01, 1, 1, 100),
        (Command.ACK, 0x05, 255, 255, 1000),
        (Command.RETURN, 0xFF, 128, 100, 65535),
    ],
)
def test_to_bytes_from_bytes(command, flags, task_id, msg_id, payload_len):
    h1 = Header(command, Flags.from_byte(flags), task_id, msg_id, payload_len)
    data = h1.to_bytes()
    h2 = Header.from_bytes(data)

    assert h2.command == command
    assert h2.flags == Flags.from_byte(flags)
    assert h2.task_id == task_id
    assert h2.payload_len == payload_len
