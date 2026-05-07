import pytest

from elasticai.experiment_framework.remote_control_v2.commands import Command
from elasticai.experiment_framework.remote_control_v2.message import Message
from elasticai.experiment_framework.remote_control_v2.message_io import MessageIO
from elasticai.experiment_framework.remote_control_v2.remote_task_controller import RemoteTaskController


class MockIOStream:
    def __init__(self, responses: list[bytes] | None = None) -> None:
        self._responses = responses or []
        self._response_index = 0
        self.written = bytearray()

    def write(self, data: bytes | bytearray, /) -> int:
        self.written.extend(data)
        return len(data)

    def read(self, num_bytes: int, /) -> bytes:
        if self._response_index >= len(self._responses):
            raise EOFError("No more responses")
        response = self._responses[self._response_index]
        self._response_index += 1
        return response


def test_open_task_assigns_msg_id_and_creates_context() -> None:
    mock_stream = MockIOStream()
    io = MessageIO(mock_stream)
    controller = RemoteTaskController(io)

    context = controller.open_task(func_id=2, payload=b"hello")

    assert context.request_msg_id != 0
    assert context.state == "opening"
    assert mock_stream.written

    message = Message.from_bytes(bytes(mock_stream.written))
    assert message.header.command == Command.OPEN_TASK
    assert message.header.msg_id == context.request_msg_id
    assert message.payload == (2).to_bytes(4, "little") + b"hello"


def test_handle_return_sets_task_id() -> None:
    mock_stream = MockIOStream()
    io = MessageIO(mock_stream)
    controller = RemoteTaskController(io)

    context = controller.open_task(func_id=3, payload=b"")
    return_payload = (123).to_bytes(4, "little")
    response = Message(Command.RETURN, return_payload, msg_id=context.request_msg_id)

    handled_context = controller.handle_incoming_message(response)

    assert handled_context is not None
    assert handled_context.task_id == 123
    assert handled_context.state == "opened"
    assert controller.active_context is handled_context


def test_send_data_chunk_uses_task_id_and_data_id() -> None:
    mock_stream = MockIOStream()
    io = MessageIO(mock_stream)
    controller = RemoteTaskController(io)

    context = controller.open_task(func_id=4, payload=b"")
    response = Message(Command.RETURN, (456).to_bytes(4, "little"), msg_id=context.request_msg_id)
    controller.handle_incoming_message(response)

    chunk_msg_id = controller.send_data_chunk(b"payload")
    all_written = bytes(mock_stream.written)

    first_msg = Message.from_bytes(all_written)
    first_size = 6 + len(first_msg.payload)
    second_msg = Message.from_bytes(all_written[first_size:])

    assert chunk_msg_id != 0
    assert second_msg.header.command == Command.DATA_CHUNK
    assert second_msg.header.msg_id == chunk_msg_id
    assert second_msg.payload[:4] == (456).to_bytes(4, "little")
    assert second_msg.payload[4:8] == (0).to_bytes(4, "little")
    assert second_msg.payload[8:] == b"payload"


def test_handle_incoming_data_chunk_verifies_expected_text() -> None:
    mock_stream = MockIOStream()
    io = MessageIO(mock_stream)
    controller = RemoteTaskController(io)

    context = controller.open_task(func_id=5, payload=b"")
    response = Message(Command.RETURN, (789).to_bytes(4, "little"), msg_id=context.request_msg_id)
    controller.handle_incoming_message(response)
    controller.expect_response_text(b"result")

    incoming = Message(
        Command.DATA_CHUNK,
        (789).to_bytes(4, "little") + (0).to_bytes(4, "little") + b"result",
        msg_id=0,
    )

    handled = controller.handle_incoming_message(incoming)

    assert handled is controller.active_context
    assert handled is not None
    assert handled.received_data == b"result"
    assert handled.verification_passed is True


def test_open_task_data_chunk_sequence_receive_response_and_close_flow() -> None:
    mock_stream = MockIOStream()
    io = MessageIO(mock_stream)
    controller = RemoteTaskController(io)

    # Open task request
    context = controller.open_task(func_id=7, payload=b"start")
    assert context.request_msg_id != 0
    assert context.state == "opening"

    # Remote RETURN opens the task and assigns task_id
    open_return = Message(
        Command.RETURN,
        (321).to_bytes(4, "little"),
        msg_id=context.request_msg_id,
    )

    opened_context = controller.handle_incoming_message(open_return)
    assert opened_context is context
    assert context.task_id == 321
    assert context.state == "opened"
    assert controller.active_context is context

    # Send two DATA_CHUNK messages: payload then empty terminator
    first_chunk_id = controller.send_data_chunk(b"hello")
    second_chunk_id = controller.send_data_chunk(b"")

    assert first_chunk_id != second_chunk_id
    assert first_chunk_id != context.request_msg_id
    assert second_chunk_id != context.request_msg_id

    written = bytes(mock_stream.written)
    offset = 0
    messages: list[Message] = []
    while offset < len(written):
        msg = Message.from_bytes(written[offset:])
        messages.append(msg)
        offset += len(msg.to_bytes())

    assert len(messages) == 3
    assert messages[0].header.command == Command.OPEN_TASK
    assert messages[1].header.command == Command.DATA_CHUNK
    assert messages[1].header.msg_id == first_chunk_id
    assert messages[1].payload[:4] == (321).to_bytes(4, "little")
    assert messages[1].payload[4:8] == (0).to_bytes(4, "little")
    assert messages[1].payload[8:] == b"hello"
    assert messages[2].header.command == Command.DATA_CHUNK
    assert messages[2].header.msg_id == second_chunk_id
    assert messages[2].payload[:4] == (321).to_bytes(4, "little")
    assert messages[2].payload[4:8] == (1).to_bytes(4, "little")
    assert messages[2].payload[8:] == b""

    # Receive a DATA_CHUNK response and then a final RETURN to close the task
    controller.expect_response_text(b"ok")
    response_chunk = Message(
        Command.DATA_CHUNK,
        (321).to_bytes(4, "little") + (0).to_bytes(4, "little") + b"ok",
        msg_id=0,
    )

    received = controller.handle_incoming_message(response_chunk)
    assert received is context
    assert context.received_data == b"ok"
    assert context.verification_passed is True
    assert controller.active_context is context

    final_return = Message(Command.RETURN, bytes(), msg_id=0)
    finished_context = controller.handle_incoming_message(final_return)

    assert finished_context is context
    assert finished_context.state == "finished"
    assert controller.active_context is None


if __name__ == "__main__":
    pytest.main([__file__])
