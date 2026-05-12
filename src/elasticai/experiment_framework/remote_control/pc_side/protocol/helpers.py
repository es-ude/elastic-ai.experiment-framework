import logging
from typing import Any, Dict

from .commands import Command
from .constants import NUM_BYTES_FOR_ID
from .message import Message

_logger = logging.getLogger(__name__)


def interpret_message(msg: Message, byte_order: str = "little") -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "command": msg.header.command,
        "transaction_id": msg.header.transaction_id,
        "flags": msg.header.flags,
    }

    match msg.header.command:
        case Command.ACK:
            data_id = (
                int.from_bytes(msg.payload[:NUM_BYTES_FOR_ID], byte_order)
                if len(msg.payload) >= NUM_BYTES_FOR_ID
                else None
            )
            result["data"] = {"data_id": data_id}
            result["acknowledged"] = True

        case Command.NACK:
            data_id = (
                int.from_bytes(msg.payload[:NUM_BYTES_FOR_ID], byte_order)
                if len(msg.payload) >= NUM_BYTES_FOR_ID
                else None
            )
            result["data"] = {"data_id": data_id}
            result["acknowledged"] = False

        case Command.OPEN_TASK:
            if len(msg.payload) >= NUM_BYTES_FOR_ID:
                func_id = int.from_bytes(msg.payload[:NUM_BYTES_FOR_ID], byte_order)
                extra = msg.payload[NUM_BYTES_FOR_ID:]
                result["data"] = {"func_id": func_id, "payload": extra}
            else:
                result["data"] = None
                _logger.warning("OPEN_TASK insufficient payload")

        case Command.DATA_CHUNK:
            if len(msg.payload) >= NUM_BYTES_FOR_ID:
                data_id = int.from_bytes(msg.payload[:NUM_BYTES_FOR_ID], byte_order)
                chunk = msg.payload[NUM_BYTES_FOR_ID:]
                result["data"] = {"data_id": data_id, "chunk": chunk}
            else:
                result["data"] = None
                _logger.warning("DATA_CHUNK insufficient payload")

        case Command.RETURN:
            result["data"] = msg.payload

        case Command.HANDSHAKE:
            result["data"] = msg.payload

        case _:
            result["data"] = msg.payload
            _logger.warning("unknown command: %s", msg.header.command)

    _logger.debug("interpreted: %s", result)
    return result


def format_message(msg: Message, byte_order: str = "little") -> str:
    header = msg.header
    parts = [
        f"command={header.command.name}",
        f"flags={header.flags}",
        f"transaction_id={header.transaction_id}",
        f"payload_len={header.payload_len}",
    ]

    match header.command:
        case Command.OPEN_TASK:
            if len(msg.payload) >= NUM_BYTES_FOR_ID:
                func_id = int.from_bytes(
                    msg.payload[:NUM_BYTES_FOR_ID], byte_order, signed=False
                )
                extra = msg.payload[NUM_BYTES_FOR_ID:]
                parts += [
                    f"func_id={func_id}",
                    f"payload={extra.hex() or '<empty>'}",
                ]
            else:
                parts.append(f"payload={msg.payload.hex() or '<empty>'}")

        case Command.DATA_CHUNK:
            if len(msg.payload) >= NUM_BYTES_FOR_ID:
                data_id = int.from_bytes(
                    msg.payload[:NUM_BYTES_FOR_ID], byte_order, signed=False
                )
                chunk = msg.payload[NUM_BYTES_FOR_ID:]  # ← no task_id
                parts += [
                    f"data_id={data_id}",
                    f"chunk={chunk.hex() or '<empty>'}",
                ]
            else:
                parts.append(f"payload={msg.payload.hex() or '<empty>'}")

        case Command.ACK | Command.NACK:
            if len(msg.payload) >= NUM_BYTES_FOR_ID:
                data_id = int.from_bytes(
                    msg.payload[:NUM_BYTES_FOR_ID], byte_order, signed=False
                )
                parts.append(f"data_id={data_id}")
            else:
                parts.append("data_id=<missing>")

        case Command.RETURN:
            parts.append(f"payload={msg.payload.hex() or '<empty>'}")

        case _:
            parts.append(f"payload={msg.payload.hex() or '<empty>'}")

    return " | ".join(parts)
