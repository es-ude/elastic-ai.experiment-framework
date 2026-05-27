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


def test_ack_and_nack_use_data_id():
    builder = MessageBuilder().set_command(Command.ACK).set_data_id(5)

    msg = builder.build()

    assert msg.payload.startswith((5).to_bytes(NUM_BYTES_FOR_ID, "little"))


def test_open_task_uses_func_id():

    builder = MessageBuilder().set_command(Command.OPEN_TASK).set_func_id(9)

    msg = builder.build()

    assert msg.payload == (9).to_bytes(NUM_BYTES_FOR_ID, "little")


def test_close_task_empty_payload():
    builder = MessageBuilder().set_command(Command.CLOSE_TASK)

    msg = builder.build()

    assert msg.payload == b""


def test_data_chunk_payload_structure():
    builder = (
        MessageBuilder().set_command(Command.DATA_CHUNK).set_data_id(3).set_data(b"ABC")
    )

    msg = builder.build()

    expected_prefix = (3).to_bytes(NUM_BYTES_FOR_ID, "little")

    assert msg.payload == expected_prefix + b"ABC"


def test_return_pass_through():
    builder = MessageBuilder().set_command(Command.RETURN).set_data(b"HELLO")

    msg = builder.build()

    assert msg.payload == b"HELLO"


def test_flags_set_correctly():
    builder = (
        MessageBuilder()
        .set_command(Command.OPEN_TASK)
        .set_need_ack(True)
        .set_is_last(True)
    )

    msg = builder.build()

    assert msg.header.flags.to_byte() & 0x1
    assert msg.header.flags.to_byte() & 0x3


def test_transaction_id_passed():
    builder = MessageBuilder().set_command(Command.ACK).set_transaction_id(42)

    msg = builder.build()

    assert msg.header.transaction_id == 42


def test_unknown_command_raises():
    b = MessageBuilder()
    b.command = Command.HANDSHAKE

    with pytest.raises(Exception):
        b.build()
