from typing import Literal

from .commands import Command
from .constants import NUM_BYTES_FOR_ID
from .flags import Flags
from .message import Message


class MessageBuilder:
    def __init__(self) -> None:
        self.data = b""
        self.byte_order: Literal["big", "little"] = "little"
        self.command: Command = Command.NACK
        self.func_id = 0
        self.data_id = 0
        self.transaction_id = 0
        self.need_ack = False

    def set_command(self, cmd: Command) -> "MessageBuilder":
        self.command = cmd
        return self

    def set_transaction_id(self, tid: int) -> "MessageBuilder":
        self.transaction_id = tid
        return self

    def set_func_id(self, fid: int) -> "MessageBuilder":
        self.func_id = fid
        return self

    def set_data_id(self, did: int) -> "MessageBuilder":
        self.data_id = did
        return self

    def set_data(self, data: bytes) -> "MessageBuilder":
        self.data = data
        return self

    def set_need_ack(self, ack: bool) -> "MessageBuilder":
        self.need_ack = ack
        return self

    def build(self) -> Message:
        match self.command:
            case Command.NACK | Command.ACK:
                return self._new_msg(self._get_number_in_bytes(self.data_id))
            case Command.OPEN_TASK:
                return self._new_msg(self._get_number_in_bytes(self.func_id))
            case Command.CLOSE_TASK:
                return self._new_msg(b"")
            case Command.DATA_CHUNK:
                return self._new_msg(
                    self._get_number_in_bytes(self.data_id) + self.data
                )
            case Command.RETURN:
                return self._new_msg(self.data)
            case _:
                raise NotImplementedError(
                    f"Command {self.command} not implemented in MessageBuilder"
                )

    def _get_number_in_bytes(self, number: int) -> bytes:
        return number.to_bytes(
            length=NUM_BYTES_FOR_ID, byteorder=self.byte_order, signed=False
        )

    def _new_msg(self, data: bytes) -> Message:
        return Message(
            self.command,
            data,
            flags=Flags(need_ack=self.need_ack).to_byte(),
            transaction_id=self.transaction_id,
            byte_order=self.byte_order,
        )
