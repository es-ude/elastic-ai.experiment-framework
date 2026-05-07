import logging
import threading
from dataclasses import dataclass, field
from typing import Dict, Literal, Optional

from .commands import Command
from .message import Message
from .message_builder import MessageBuilder
from .message_io import MessageIO
from .constants import MAX_MSG_ID, NUM_BYTES_FOR_ID


@dataclass
class TaskContext:
    request_msg_id: int
    task_id: Optional[int] = None
    next_data_id: int = 0
    state: str = "opening"
    expected_response_text: bytes = field(default_factory=bytes)
    received_data: bytearray = field(default_factory=bytearray)
    verification_passed: Optional[bool] = None
    opened_event: threading.Event = field(default_factory=threading.Event)
    finished_event: threading.Event = field(default_factory=threading.Event)


class RemoteTaskController:
    """Manage a single open-task context with msg_id/task_id correlation."""

    def __init__(self, message_io: MessageIO, byte_order: Literal["big", "little"] = "little") -> None:
        self._message_io = message_io
        self._byte_order = byte_order
        self._logger = logging.getLogger(__name__)
        self._lock = threading.Lock()
        self._last_msg_id = 0
        self._pending_contexts: Dict[int, TaskContext] = {}
        self._active_context: Optional[TaskContext] = None

    @property
    def active_context(self) -> Optional[TaskContext]:
        return self._active_context

    def _next_msg_id(self) -> int:
        self._last_msg_id = (self._last_msg_id + 1) & MAX_MSG_ID
        if self._last_msg_id == 0:
            self._last_msg_id = 1
        return self._last_msg_id

    def _to_bytes(self, value: int) -> bytes:
        return value.to_bytes(NUM_BYTES_FOR_ID, byteorder=self._byte_order, signed=False)

    def _write_message(self, msg: Message) -> None:
        with self._lock:
            self._message_io.write(msg)
            self._logger.debug("Sent %s", msg)

    def open_task(self, func_id: int, payload: bytes = b"") -> TaskContext:
        if self._active_context is not None:
            raise RuntimeError("Only one active task context is allowed")

        msg_id = self._next_msg_id()
        ctx = TaskContext(request_msg_id=msg_id)
        self._pending_contexts[msg_id] = ctx

        builder = MessageBuilder()
        builder.byte_order = self._byte_order
        builder.command = Command.OPEN_TASK
        builder.func_id = func_id
        builder.data = payload
        builder.msg_id = msg_id
        msg = next(builder.build())
        self._write_message(msg)

        self._logger.info("Opened task context request msg_id=%d", msg_id)
        return ctx

    def send_data_chunk(self, text: bytes = b"") -> int:
        if self._active_context is None or self._active_context.task_id is None:
            raise RuntimeError("No active task context available")

        msg_id = self._next_msg_id()
        context = self._active_context
        builder = MessageBuilder()
        builder.byte_order = self._byte_order
        builder.command = Command.DATA_CHUNK
        builder.task_id = context.task_id
        builder.data_id = context.next_data_id
        builder.data = text
        builder.msg_id = msg_id
        msg = next(builder.build())
        context.next_data_id += 1
        self._write_message(msg)

        self._logger.info(
            "Sent DATA_CHUNK msg_id=%d task_id=%s data_id=%d payload_len=%d",
            msg_id,
            context.task_id,
            context.next_data_id - 1,
            len(text),
        )
        return msg_id

    def expect_response_text(self, expected: bytes) -> None:
        if self._active_context is None:
            raise RuntimeError("No active task context available")
        self._active_context.expected_response_text = expected

    def handle_incoming_message(self, msg: Message) -> Optional[TaskContext]:
        context = self._pending_contexts.pop(msg.header.msg_id, None)

        if msg.header.command == Command.RETURN:
            if context is not None and context.state == "opening":
                task_id = self._parse_task_id(msg.payload)
                context.task_id = task_id
                context.state = "opened"
                context.opened_event.set()
                self._active_context = context
                self._logger.info("Task opened msg_id=%d task_id=%d", msg.header.msg_id, task_id)
                return context

            if self._active_context is not None and self._active_context.task_id is not None:
                self._active_context.state = "finished"
                self._active_context.finished_event.set()
                self._logger.info(
                    "Task finished task_id=%d msg_id=%d",
                    self._active_context.task_id,
                    msg.header.msg_id,
                )
                finished_context = self._active_context
                self._active_context = None
                return finished_context

            self._logger.debug("Received RETURN with no matching context msg_id=%d", msg.header.msg_id)
            return None

        if msg.header.command == Command.DATA_CHUNK and self._active_context is not None:
            task_id = self._parse_task_id(msg.payload)
            data_id = int.from_bytes(msg.payload[NUM_BYTES_FOR_ID:NUM_BYTES_FOR_ID*2], byteorder=self._byte_order, signed=False)
            chunk_data = msg.payload[NUM_BYTES_FOR_ID*2:]

            if task_id != self._active_context.task_id:
                self._logger.warning(
                    "Received DATA_CHUNK for unexpected task_id=%d (active=%s)",
                    task_id,
                    self._active_context.task_id,
                )
                return None

            self._active_context.received_data.extend(chunk_data)
            self._active_context.state = "received_data"
            self._active_context.verification_passed = (
                chunk_data == self._active_context.expected_response_text
            )
            self._logger.info(
                "Received DATA_CHUNK task_id=%d data_id=%d len=%d verified=%s",
                task_id,
                data_id,
                len(chunk_data),
                self._active_context.verification_passed,
            )
            return self._active_context

        self._logger.warning("Unhandled incoming message: %s", msg)
        return None

    def receive_and_handle_once(self) -> Optional[TaskContext]:
        msg = self._message_io.read()
        return self.handle_incoming_message(msg)

    def _parse_task_id(self, payload: bytes) -> int:
        if len(payload) < NUM_BYTES_FOR_ID:
            raise ValueError("Payload is too short to contain a task_id")
        return int.from_bytes(payload[:NUM_BYTES_FOR_ID], byteorder=self._byte_order, signed=False)
