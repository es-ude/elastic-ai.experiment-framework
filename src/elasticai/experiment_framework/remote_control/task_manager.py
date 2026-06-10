import asyncio
import logging
from typing import AsyncIterable, Awaitable, Callable, Dict

from .callback_actions import CallbackAction, CloseTask, NoAction, SendChunk
from .commands import Command
from .constants import (
    MAX_TASKS,
    NUM_MAX_RETRIES,
    RESPONSE_TIMEOUT,
    RETURN_CODE_OFFSET,
)
from .exceptions import (
    MessageRetransmissionError,
    ReceivedNackError,
    UnexpectedMessageError,
)
from .helpers import format_message
from .message import Message
from .message_builder import MessageBuilder
from .message_io import MessageIO
from .task import Task, TaskState

_logger = logging.getLogger(__name__)


class TaskManager:
    def __init__(self, device: MessageIO, timeout: float = RESPONSE_TIMEOUT) -> None:
        self._device = device
        self._running_tasks: Dict[int, Task] = {}
        self._receiver: asyncio.Task
        self._receiver_started = asyncio.Event()
        self._timeout = timeout

    async def start(self) -> None:
        self._receiver = asyncio.create_task(self._receive_loop())
        await self._receiver_started.wait()

    async def stop(self) -> None:
        self._running = False
        if self._receive_loop:
            self._receiver.cancel()

    async def open_task(self, task: Task, need_ack: bool | None = None):
        task._completion = asyncio.get_running_loop().create_future()

        task_id = self._next_task_id()
        task._state = TaskState.OPENING

        task._task_id = task_id
        msg_id = task._next_msg_id

        self._running_tasks[task_id] = task

        need_ack = (need_ack is not None and need_ack) or (
            need_ack is None and task.need_ack
        )
        await self._send_message(
            command=Command.OPEN_TASK,
            task_id=task_id,
            msg_id=msg_id,
            task_def_id=task.task_def_id,
            need_ack=need_ack,
        )

        task._state = TaskState.OPENED
        task._next_msg_id += 1

        await self._run_callback(task, task.on_opened())

    async def close_task(self, task: Task, need_ack: bool | None = None) -> None:
        task = self._running_tasks[task.task_id]

        if not (task._state == TaskState.OPENING or task._state == TaskState.CLOSING):
            task._state = TaskState.CLOSING

            need_ack = (need_ack is not None and need_ack) or (
                need_ack is None and task.need_ack
            )

            msg_id = task._next_msg_id
            await self._send_message(
                command=Command.CLOSE_TASK,
                msg_id=msg_id,
                task_id=task.task_id,
                need_ack=need_ack,
            )

            task._state = TaskState.CLOSED
            task._next_msg_id += 1

            self._running_tasks.pop(task.task_id)

    async def send_chunk(
        self, task: Task, data: bytes, need_ack: bool | None = None
    ) -> None:
        task = self._running_tasks[task.task_id]
        msg_id = task._next_msg_id

        need_ack = need_ack or (need_ack is None and task.need_ack)

        try:
            await self._send_message(
                command=Command.DATA_CHUNK,
                task_id=task.task_id,
                msg_id=msg_id,
                data=data,
                need_ack=need_ack,
            )
            task._next_msg_id += 1

        except ReceivedNackError:
            task._pending_acks.pop(msg_id, None)

            raise RuntimeError(
                f"[Client] Nack received task_id={task.task_id} msg_id={msg_id}"
            )

    async def _on_message(self, message: Message) -> None:
        try:
            task_id = message.header.task_id
            need_ack = message.header.flags.need_ack

            task = self._running_tasks.get(task_id)

            if task is None:
                _logger.warning("[CLIENT]unknown task_id=%d", task_id)
                if need_ack:
                    await self._send_nack(message)
                    return
                raise UnexpectedMessageError("%s", message)

            handlers: dict[
                Command,
                Callable[
                    [Task, Message],
                    Awaitable[None],
                ],
            ] = {
                Command.ACK: self._handle_ack,
                Command.NACK: self._handle_nack,
                Command.DATA_CHUNK: self._handle_chunk,
                Command.RETURN: self._handle_return,
            }

            handler = handlers.get(message.header.command)

            if handler is None:
                _logger.warning(
                    "[CLIENT]  unsupported command=%s",
                    message.header.command,
                )
                return

            await handler(task, message)

        except UnexpectedMessageError:
            raise UnexpectedMessageError()

        except Exception as e:
            _logger.error("[CLIENT]error handling message: %s", e)
            raise

    async def _send_nack(self, msg: Message):
        task_id = msg.header.task_id

        await self._send_message(
            command=Command.NACK, task_id=task_id, msg_id=msg.header.msg_id
        )

    async def _handle_ack(
        self,
        task: Task,
        message: Message,
    ) -> None:
        msg_id = message.header.msg_id

        fut = task._pending_acks.pop(msg_id, None)

        if fut is None:
            _logger.warning(
                "[CLIENT]  unexpected ACK task_id=%d msg_id=%d",
                task.task_id,
                msg_id,
            )
            return

        if not fut.done():
            fut.set_result(True)

    async def _handle_nack(
        self,
        task: Task,
        message: Message,
    ) -> None:
        msg_id = message.header.msg_id

        fut = task._pending_acks.pop(msg_id, None)

        if fut is None:
            _logger.warning(
                "[CLIENT]  Unexpected NACK task_id=%d msg_id=%d",
                task.task_id,
                msg_id,
            )
            return

        if not fut.done():
            _logger.error(
                "[CLIENT]  NACK task_id=%d msg_id=%d",
                task.task_id,
                msg_id,
            )
            fut.set_exception(ReceivedNackError())

    async def _handle_chunk(
        self,
        task: Task,
        message: Message,
    ) -> None:

        flags = message.header.flags
        msg_id = message.header.msg_id
        task._received_data[msg_id] = message.payload
        task._state = TaskState.RECEIVED_DATA

        if flags.need_ack:
            await self._send_message(
                command=Command.ACK, task_id=task.task_id, msg_id=msg_id
            )

        await self._run_callback(task, task.on_data_chunk_received())

    async def _handle_return(
        self,
        task: Task,
        message: Message,
    ) -> None:
        if task._completion is not None and not task._completion.done():
            task._state = TaskState.RETURNED
            return_code = message.payload[RETURN_CODE_OFFSET]

            task._completion.set_result(return_code)

            flags = message.header.flags

            if flags.need_ack:
                await self._send_message(
                    Command.ACK,
                    task_id=task.task_id,
                    msg_id=message.header.msg_id,
                )

        await self._run_callback(task, task.on_return())

    async def _send_message(
        self,
        command: Command,
        task_id: int,
        msg_id: int,
        *,
        task_def_id: int = 0,
        data: bytes = b"",
        need_ack: bool = False,
    ) -> None:
        builder = (
            MessageBuilder()
            .set_command(command)
            .set_task_id(task_id)
            .set_msg_id(msg_id)
            .set_task_def_id(task_def_id)
            .set_data(data)
            .set_need_ack(need_ack)
        )

        message = builder.build()

        await self._device.write(message)

        if command == Command.ACK or command == Command.NACK:
            return

        if need_ack:
            task = self._running_tasks.get(task_id, None)
            if task is None:
                raise RuntimeError(f"[client] no task found with id {task_id}")
            attempt = 0

            while True:
                try:
                    fut = asyncio.get_running_loop().create_future()
                    task._pending_acks[msg_id] = fut

                    await asyncio.wait_for(fut=fut, timeout=self._timeout)
                    return

                except ReceivedNackError:
                    return
                except TimeoutError:
                    attempt += 1
                    if attempt > NUM_MAX_RETRIES:
                        break

                    _logger.warning(
                        "[Client] Message retransmissionmessage:%s number attempts:%d",
                        format_message(message),
                        attempt,
                    )
                    await self._device.write(message)

            raise MessageRetransmissionError(
                f"Failed to send the message after {NUM_MAX_RETRIES} retries:{message}"
            )

    async def _run_callback(self, task: Task, cb: AsyncIterable[CallbackAction]):
        async for action in cb:
            await self._handle_action(task, action)

    async def _handle_action(self, task: Task, action: CallbackAction) -> None:
        match action:
            case NoAction():
                pass
            case SendChunk(data, need_ack):
                await self.send_chunk(task, data, need_ack)
            case CloseTask(need_ack):
                await self.close_task(task, need_ack)
            case _:
                _logger.warning("[CLIENT] unknown action: %s", action)

    def _next_task_id(self) -> int:
        used = set(self._running_tasks.keys())

        for task_id in range(0, MAX_TASKS):
            if task_id not in used:
                return task_id

        raise RuntimeError(f"[Client]all {MAX_TASKS} transaction IDs in use")

    async def _receive_loop(self) -> None:
        self._running = True
        self._receiver_started.set()

        while self._running:
            message = await self._device.read()
            await self._on_message(message)

        self._running = False
