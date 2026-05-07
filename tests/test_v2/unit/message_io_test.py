from typing import Self
import pytest

from elasticai.experiment_framework.remote_control_v2.commands import Command
from elasticai.experiment_framework.remote_control_v2.message import Message
from elasticai.experiment_framework.remote_control_v2.remote_control_protocol import RemoteControlProtocol
from elasticai.experiment_framework.remote_control_v2.remote_control import RemoteControl


class MockIOStream:
    def __init__(self, response: bytes) -> None:
        self._response = bytearray(response)
        self.written   = bytearray()

    def write(self, data: bytes | bytearray, /) -> int:
        self.written.extend(data)
        return len(data)

    def read(self, num_bytes: int, /) -> bytes:
        result        = bytes(self._response[:num_bytes])
        self._response = self._response[num_bytes:]
        return result
    
    

def make_return(payload: bytes) -> bytes:
    """Build a fake RETURN message from the board"""
    return Message(Command.RETURN, payload).to_bytes()


def parse_messages(raw: bytes) -> list[Message]:
    messages: list[Message] = []
    offset = 0
    while offset < len(raw):
        msg = Message.from_bytes(raw[offset:])
        messages.append(msg)
        offset += len(msg.to_bytes())
    return messages


def test_echo_success():
    data     = bytes([0xAB, 0xCD])
    mock     = MockIOStream(response=make_return(data))
    protocol = RemoteControlProtocol(mock)

    result = protocol.echo(data)

    assert result == data


def test_echo_wrong_response():
    data     = bytes([0xAB, 0xCD])
    wrong    = bytes([0x00, 0x00])
    mock     = MockIOStream(response=make_return(wrong))
    protocol = RemoteControlProtocol(mock)

    result = protocol.echo(data)

    assert result != data


def test_message_sent_correctly():
    data     = bytes([0xAB, 0xCD])
    mock     = MockIOStream(response=make_return(data))
    protocol = RemoteControlProtocol(mock)

    protocol.echo(data)

    sent = Message.from_bytes(mock.written)
    assert sent.header.command  == Command.OPEN_TASK
    assert sent.payload         == bytes([0]) + data


def test_message_roundtrip():
    original = Message(Command.OPEN_TASK, bytes([0, 0xAB, 0xCD]))
    restored = Message.from_bytes(original.to_bytes())

    assert original == restored


def test_call_function_sends_task_flow_and_returns_response():
    response_payload = b"pong"
    response_messages = (
        Message(Command.RETURN, (42).to_bytes(4, "little")).to_bytes()
        + Message(Command.DATA_CHUNK, (42).to_bytes(4, "little") + (0).to_bytes(4, "little") + response_payload).to_bytes()
        + Message(Command.RETURN, b"").to_bytes()
    )
    mock = MockIOStream(response=response_messages)
    protocol = RemoteControlProtocol(mock)

    result = protocol.call_function(func_id=1, args=b"ping")

    assert result == response_payload

    sent_messages = parse_messages(bytes(mock.written))
    assert sent_messages[0].header.command == Command.OPEN_TASK
    assert sent_messages[1].header.command == Command.DATA_CHUNK
    assert sent_messages[1].payload[8:] == b"ping"
    assert sent_messages[2].header.command == Command.DATA_CHUNK
    assert sent_messages[2].payload[8:] == b""
