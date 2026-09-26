from typing import Literal

from .commands import Command
from .constants import NUM_BYTES_FOR_ID
from .flags import Flags
from .message import Message


class MessageBuilder:
    def __init__(self) -> None:
        self.data = b""
        self.byte_order: Literal["big", "little"] = "little"
        self.command: Command
        self.task_def_id = 0
        self.task_id = 0
        self.msg_id = 0
        self.need_ack = False
        self.has_crc = False

    def set_command(self, cmd: Command) -> "MessageBuilder":
        self.command = cmd
        return self

    def set_task_id(self, task_id: int) -> "MessageBuilder":
        self.task_id = task_id
        return self

    def set_task_def_id(self, task_def_id: int) -> "MessageBuilder":
        self.task_def_id = task_def_id
        return self

    def set_msg_id(self, msg_id: int) -> "MessageBuilder":
        self.msg_id = msg_id
        return self

    def set_data(self, data: bytes) -> "MessageBuilder":
        self.data = data
        return self

    def set_need_ack(self, ack: bool) -> "MessageBuilder":
        self.need_ack = ack
        return self

    def set_crc(self, has_crc: bool) -> "MessageBuilder":
        self.has_crc = has_crc
        return self

    def build(self) -> Message:
        match self.command:
            case Command.NACK:
                return self._new_msg(self.data)
            case Command.ACK:
                return self._new_msg()
            case Command.OPEN_TASK:
                return self._new_msg(self._get_number_in_bytes(self.task_def_id))
            case Command.CLOSE_TASK:
                return self._new_msg()
            case Command.DATA_CHUNK:
                return self._new_msg(self.data)
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

    def _new_msg(self, data: bytes = b"") -> Message:
        return Message(
            self.command,
            data,
            flags=Flags(need_ack=self.need_ack, has_crc=self.has_crc).to_number(),
            task_id=self.task_id,
            msg_id=self.msg_id,
            byte_order=self.byte_order,
        )
