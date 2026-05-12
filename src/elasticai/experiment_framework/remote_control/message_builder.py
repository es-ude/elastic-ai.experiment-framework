from collections.abc import Iterator
from enum import Flag
from typing import Iterable, Literal

from elasticai.experiment_framework.remote_control.flags import Flags

from .commands import Command
from .message import Message
from .constants import NUM_BYTES_FOR_ID

class MessageBuilder:
    def __init__(self) -> None:
        self.data = b""
        self.byte_order: Literal["big", "little"] = "little"
        self._NUM_BYTES_FOR_LENGTH = NUM_BYTES_FOR_ID
        self.command: Command = Command.NACK
        self.func_id = 0
        self.data_id = 0
        self.transaction_id = 0
        self.need_ack = False
        self.is_last = False

    def set_command(self, cmd: Command)      -> "MessageBuilder": self.command        = cmd;  return self
    def set_transaction_id(self, tid: int)   -> "MessageBuilder": self.transaction_id = tid;  return self
    def set_func_id(self, fid: int)          -> "MessageBuilder": self.func_id        = fid;  return self
    def set_data_id(self, did: int)          -> "MessageBuilder": self.data_id        = did;  return self
    def set_data(self, data: bytes)          -> "MessageBuilder": self.data           = data; return self
    def set_need_ack(self, ack: bool)        -> "MessageBuilder": self.need_ack       = ack;  return self
    def set_is_last(self, is_last: bool)     -> "MessageBuilder": self.is_last       = is_last;  return self

 
    def build(self) -> Iterator[Message]:
        match self.command:
            case (Command.NACK| Command.ACK):
                yield self._new_msg(self._get_number_in_bytes(self.data_id))
            case Command.OPEN_TASK:
                yield self._new_msg(
                    self._get_number_in_bytes(self.func_id)
                )
            case Command.CLOSE_TASK:
                yield self._new_msg(b"")
            case Command.DATA_CHUNK:
                yield self._new_msg(
                    self._get_number_in_bytes(self.data_id) + self.data
                )
            case Command.RETURN:
                yield self._new_msg(self.data)
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
            flags= Flags(need_ack= self.need_ack, is_last=self.is_last).to_byte(),
            transaction_id=self.transaction_id,
            byte_order=self.byte_order,
        )

