from typing import Literal

from .commands import Command
from .constants import NUM_BYTES_FOR_ID
from .message import Message


def format_message(
    msg: Message, byte_order: Literal["little", "big"] = "little"
) -> str:
    header = msg.header
    parts = [
        f"command={header.command.name}",
        f"flags={header.flags}",
        f"task_id={header.task_id}",
        f"msg_id={header.msg_id}",
        f"payload_len={header.payload_len}",
    ]

    match header.command:
        case Command.OPEN_TASK:
            if len(msg.payload) >= NUM_BYTES_FOR_ID:
                task_def_id = int.from_bytes(
                    msg.payload[:NUM_BYTES_FOR_ID], byte_order, signed=False
                )
                extra = msg.payload[NUM_BYTES_FOR_ID:]
                parts += [
                    f"task_def_id={task_def_id}",
                    f"payload={extra.hex() or '<empty>'}",
                ]
            else:
                parts.append(f"payload={msg.payload.hex() or '<empty>'}")

        case _:
            parts.append(f"payload={msg.payload.hex() or '<empty>'}")

    return " | ".join(parts)
