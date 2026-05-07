import logging
from typing import Any, Dict

from .commands import Command
from .constants import NUM_BYTES_FOR_ID
from .message import Message

_logger = logging.getLogger(__name__)


def interpret_message(msg: Message, byte_order: str = "little") -> Dict[str, Any]:
    """Interpret a received Message object and return structured payload data."""
    result: Dict[str, Any] = {
        'command': msg.header.command,
        'msg_id': msg.header.msg_id,
        'flags': msg.header.flags,
    }

    match msg.header.command:
        case Command.ACK:
            result['data'] = None
            result['acknowledged'] = True
        case Command.NACK:
            result['data'] = None
            result['acknowledged'] = False
        case Command.OPEN_TASK:
            if len(msg.payload) >= NUM_BYTES_FOR_ID:
                func_id = int.from_bytes(msg.payload[:NUM_BYTES_FOR_ID], byteorder=byte_order)
                result['data'] = {'func_id': func_id}
            else:
                result['data'] = None
                _logger.warning("OPEN_TASK message has insufficient payload")
        case Command.CLOSE_TASK:
            if len(msg.payload) >= NUM_BYTES_FOR_ID:
                task_id = int.from_bytes(msg.payload[:NUM_BYTES_FOR_ID], byteorder=byte_order)
                result['data'] = {'task_id': task_id}
            else:
                result['data'] = None
                _logger.warning("CLOSE_TASK message has insufficient payload")
        case Command.DATA_CHUNK:
            if len(msg.payload) >= NUM_BYTES_FOR_ID * 2:
                task_id = int.from_bytes(msg.payload[:NUM_BYTES_FOR_ID], byteorder=byte_order)
                data_id = int.from_bytes(msg.payload[NUM_BYTES_FOR_ID:NUM_BYTES_FOR_ID*2], byteorder=byte_order)
                chunk_data = msg.payload[NUM_BYTES_FOR_ID*2:]
                result['data'] = {
                    'task_id': task_id,
                    'data_id': data_id,
                    'chunk_data': chunk_data,
                }
            else:
                result['data'] = None
                _logger.warning("DATA_CHUNK message has insufficient payload")
        case Command.RETURN:
            result['data'] = msg.payload
        case Command.HANDSHAKE:
            result['data'] = msg.payload
        case _:
            result['data'] = msg.payload
            _logger.warning(f"Unknown command received: {msg.header.command}")

    _logger.debug("Interpreted message: %s", result)
    return result


def format_message(msg: Message, byte_order: str = "little") -> str:
    header = msg.header
    parts = [
        f"command={header.command.name}",
        f"flags={header.flags}",
        f"msg_id={header.msg_id}",
        f"payload_len={header.payload_len}",
    ]

    if header.command == Command.OPEN_TASK:
        if len(msg.payload) >= 1:
            func_id = int.from_bytes(msg.payload[:1], byteorder=byte_order, signed=False)
            payload = msg.payload[1:]
            parts.append(f"func_id={func_id}")
            parts.append(f"payload={payload.hex() or '<empty>'}")
        else:
            parts.append(f"payload={msg.payload.hex() or '<empty>'}")
    elif header.command == Command.DATA_CHUNK:
        if len(msg.payload) >= 2:
            task_id = int.from_bytes(msg.payload[:1], byteorder=byte_order, signed=False)
            data_id = int.from_bytes(msg.payload[1:2], byteorder=byte_order, signed=False)
            chunk = msg.payload[2:]
            parts.append(f"task_id={task_id}")
            parts.append(f"data_id={data_id}")
            parts.append(f"chunk={chunk.hex() or '<empty>'}")
        else:
            parts.append(f"payload={msg.payload.hex() or '<empty>'}")
    elif header.command == Command.RETURN:
        if len(msg.payload) >= 1:
            task_id = int.from_bytes(msg.payload[:1], byteorder=byte_order, signed=False)
            parts.append(f"task_id={task_id}")
            if len(msg.payload) > 1:
                parts.append(f"payload={msg.payload[1:].hex() or '<empty>'}")
        else:
            parts.append(f"payload={msg.payload.hex() or '<empty>'}")
    else:
        parts.append(f"payload={msg.payload.hex() or '<empty>'}")

    return " | ".join(parts)

