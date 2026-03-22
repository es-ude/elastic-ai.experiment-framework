from elasticai.experiment_framework.remote_control.commands import Command
from elasticai.experiment_framework.remote_control.message import Message
from elasticai.experiment_framework.remote_control.message_builder import MessageBuilder


def test_mcu_led2_creates_correct_message():
    b = MessageBuilder()
    b.command = Command.MCU_LEDS
    b.payload = b"\x02"
    expected = Message(Command.MCU_LEDS, b"\x02", byte_order="big")
    actual = next(iter(b.build()))
    assert actual == expected


def test_mcu_led2_yields_correct_byte_sequence():
    b = MessageBuilder()
    b.command = Command.MCU_LEDS
    b.payload = b"\x02"
    expected = b"\x08\x00\x00\x00\x01\x02\x0b"
    actual = next(iter(b.build())).to_bytes()
    assert actual == expected


def test_messages_are_cut_into_chunks():
    b = MessageBuilder()
    b.command = 255
    b.payload = bytes(list(range(255)))
    b.expected_response_size = 10
    b.flash_chunk_size = 254
    msgs = list(b.build())
    assert list(range(255)) == [int(elem) for msg in msgs[1:] for elem in msg.payload]
    assert all(map(lambda x: len(x.payload) <= 254, msgs))
    assert msgs[0].payload == bytes((0, 0, 0, 255, 0, 0, 0, 10))
