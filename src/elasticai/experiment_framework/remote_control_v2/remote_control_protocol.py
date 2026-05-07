import logging
import threading
from typing import Optional

from .commands import Command
from .io_stream import IOStream
from .message import Message
from .message_chunks_receiver import interpret_message, format_message
from .message_io import MessageIO
from .remote_task_controller import RemoteTaskController, TaskContext

_logger = logging.getLogger(__name__)


class RemoteControlProtocol:
    def __init__(self, device: IOStream) -> None:
        self._device = MessageIO(device)
        self._task_controller = RemoteTaskController(self._device, byte_order=self._device._byte_order)
        self._receive_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def send_command(
        self,
        command: Command,
        payload: bytes = b"",
        msg_id: int = 0,
    ) -> Message:
        msg = Message(command, payload, msg_id=msg_id)
        with self._lock:
            self._device.write(msg)
            return self._device.read()

    def start_receive_loop(self) -> None:
        if self._receive_thread and self._receive_thread.is_alive():
            return

        self._stop_event.clear()
        self._receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._receive_thread.start()
        _logger.info("Started remote receive loop")

    def stop_receive_loop(self) -> None:
        self._stop_event.set()
        if self._receive_thread is not None:
            self._receive_thread.join(timeout=1.0)
            _logger.info("Stopped remote receive loop")

    def _receive_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                msg = self._device.read()
                formatted = format_message(msg, byte_order=self._device._byte_order)
                _logger.debug("Incoming message: %s", formatted)
                print(f"Received: {msg.payload.hex()}")
                self._task_controller.handle_incoming_message(msg)
            except ConnectionError as exc:
                _logger.info("Receive loop stopped: %s", exc)
                break
            except Exception:
                _logger.exception("Receive loop error")
                break

    def open_task(self, func_id: int, payload: bytes = b"") -> TaskContext:
        return self._task_controller.open_task(func_id, payload)

    def send_data_chunk(self, text: bytes = b"") -> int:
        return self._task_controller.send_data_chunk(text)

    def expect_response_text(self, expected: bytes) -> None:
        self._task_controller.expect_response_text(expected)

    def process_next_message(self) -> Optional[TaskContext]:
        msg = self._device.read()
        return self._task_controller.handle_incoming_message(msg)

    @property
    def active_context(self) -> Optional[TaskContext]:
        return self._task_controller.active_context

    def call_function(self, func_id: int, args: bytes = b"", timeout: Optional[float] = None) -> bytes:
        started_receive_loop = False
        if self._receive_thread is None or not self._receive_thread.is_alive():
            _logger.info("Starting receive loop for call_function")
            self.start_receive_loop()
            started_receive_loop = True

        context = self.open_task(func_id, b"")
        _logger.info("Opened task request func_id=%d msg_id=%d", func_id, context.request_msg_id)

        if not context.opened_event.wait(timeout):
            raise TimeoutError("Timed out waiting for task open")
        _logger.info("Task opened task_id=%s", context.task_id)

        self.send_data_chunk(args)
        _logger.info("Sent args data chunk len=%d", len(args))
        self.send_data_chunk(b"")
        _logger.info("Sent empty data chunk to terminate args")

        if not context.finished_event.wait(timeout):
            raise TimeoutError("Timed out waiting for task completion")
        _logger.info("Task finished task_id=%s received len=%d", context.task_id, len(context.received_data))

        if started_receive_loop:
            self.stop_receive_loop()

        return bytes(context.received_data)

    def receive_one(self) -> Optional[Message]:
        return self._device.read()

    def echo(self, data: bytes) -> bytes:
        response = self.send_command(Command.OPEN_TASK, bytes([0]) + data)
        return response.payload
