import pytest

from elasticai.experiment_framework.remote_control.commands import (
    Command,
)
from elasticai.experiment_framework.remote_control.constants import (
    NUM_BYTES_FOR_ID,
)
from elasticai.experiment_framework.remote_control.message_builder import (
    MessageBuilder,
)


def test_ack_and_nack_empty_payload():
    builder = MessageBuilder().set_command(Command.ACK)

    msg = builder.build()

    assert msg.payload == b""


def test_open_task_uses_task_def_id():

    builder = MessageBuilder().set_command(Command.OPEN_TASK).set_task_def_id(9)

    msg = builder.build()

    assert msg.payload == (9).to_bytes(NUM_BYTES_FOR_ID, "little")


def test_close_task_empty_payload():
    builder = MessageBuilder().set_command(Command.CLOSE_TASK)

    msg = builder.build()

    assert msg.payload == b""


def test_data_chunk_payload_is_data():
    data = b"Hello world"
    builder = (
        MessageBuilder().set_command(Command.DATA_CHUNK).set_msg_id(3).set_data(data)
    )

    msg = builder.build()
    assert msg.payload == data


def test_return_pass_through():
    data = b"\x02"
    builder = MessageBuilder().set_command(Command.RETURN).set_data(data)

    msg = builder.build()

    assert msg.payload == data


def test_flags_set_correctly():
    builder = MessageBuilder().set_command(Command.OPEN_TASK).set_need_ack(True)

    msg = builder.build()

    assert msg.header.flags.to_byte() & 0x1
    assert msg.header.flags.to_byte() & 0x3


def test_task_id_passed():
    builder = MessageBuilder().set_command(Command.ACK).set_task_id(42)

    msg = builder.build()

    assert msg.header.task_id == 42


def test_unknown_command_raises():
    b = MessageBuilder()
    b.command = Command.HANDSHAKE

    with pytest.raises(Exception):
        b.build()
