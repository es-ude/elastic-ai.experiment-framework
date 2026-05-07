from collections.abc import Iterator
from typing import Iterable, Literal

from .commands import Command
from .message import Message
from .constants import NUM_BYTES_FOR_ID


def _batched_bytes(iterable: bytes | bytearray, batch_size: int) -> Iterator[bytes]:
    b = bytearray()
    for i in iterable:
        b.append(i)
        if len(b) == batch_size:
            yield bytes(b)
            b.clear()
    if len(b) > 0:
        yield bytes(b)


class MessageBuilder:
    def __init__(self) -> None:
        self.chunk_size = 1024
        self.data = bytes()
        self.num_read_bytes = 1
        self.byte_order: Literal["big", "little"] = "big"
        self._NUM_BYTES_FOR_LENGTH = NUM_BYTES_FOR_ID
        self.command: Command = Command.NACK
        self.expected_response_size = 1
        self.func_id = 0
        self.task_id = 0 
        self.data_id = 0
        self.msg_id = 0
        self.msg_id = 0

    @property
    def payload(self) -> bytes:
        return self.data

    @payload.setter
    def payload(self, v: bytes) -> None:
        self.data = v

    def build(self) -> Iterator[Message]:
        match self.command:
            case (
                Command.NACK
                | Command.ACK
            ):
                yield self._command_without_payload()
            case Command.OPEN_TASK:
                yield from self._open_task()
            case Command.DATA_CHUNK:
                yield from self._data_chunk()
            case _:
                raise NotImplementedError(f"Command {self.command} not implemented in MessageBuilder")

    def _get_number_in_bytes(self, number: int) -> bytes:
        return number.to_bytes(
            length=self._NUM_BYTES_FOR_LENGTH, byteorder=self.byte_order, signed=False
        )

    def _new_msg(self, data: bytes) -> Message:
        return Message(
            self.command,
            data,
            msg_id=self.msg_id,
            byte_order=self.byte_order,
        )

    def _command_without_payload(self) -> Message:
        return Message(self.command, bytes())

    def _simple_message_with_payload(self) -> Message:
        return self._new_msg(self.data)
    
    def _message_with_payload(self) -> Message:
        return self._new_msg(self.data)

    @property
    def _data_size_in_bytes(self) -> bytes:
        return self._get_number_in_bytes(len(self.data))



    def _data_chunk(self) -> Iterator[Message]:
        yield self._new_msg(
            b"".join((
                self._get_number_in_bytes(self.task_id),
                self._get_number_in_bytes(self.data_id),
                self.data,
            ))
        )
    def _open_task(self) -> Iterator[Message]:
        yield self._new_msg(
            b"".join((
                self._get_number_in_bytes(self.func_id),
                self.data,
            ))
        )
