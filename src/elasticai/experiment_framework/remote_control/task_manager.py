import asyncio
import logging
from typing import AsyncIterable, Awaitable, Callable, Dict

from .callback_actions import CallbackAction, CloseTask, SendChunk
from .commands import Command
from .constants import MAX_TRANSACTIONS, NUM_BYTES_OFFSET_DATA_ID_IN_PAYLOAD
from .exceptions import ReceivedNackError, UnexpectedMessageError
from .message import Message
from .message_builder import MessageBuilder
from .message_io import MessageIO
from .task import Task, TaskState

_logger = logging.getLogger(__name__)


class TaskManager:
    def __init__(self, device: MessageIO) -> None:
        self._device = device
        self._running_tasks: Dict[int, Task] = {}
        self._receiver: asyncio.Task
        self._receiver_started = asyncio.Event()

    async def start(self) -> None:
        self._receiver = asyncio.create_task(self._receive_loop())
        await self._receiver_started.wait()

    async def stop(self) -> None:
        self._running = False
        if self._receive_loop:
            self._receiver.cancel()

    async def open_task(self, task: Task, need_ack: bool | None = None) -> Task:
        tid = self._next_transaction_id()
        task._state = TaskState.OPENING
        task._transaction_id = tid
        self._running_tasks[tid] = task

        await self._send_message(
            command=Command.OPEN_TASK,
            transaction_id=tid,
            func_id=task.func_id,
            need_ack=task.need_ack,
        )
        
        need_ack = (need_ack is not None and need_ack) or (
                need_ack is None and task.need_ack
            )
        
        if need_ack:
            await asyncio.wait_for(
                task._opened_event.wait(),
                timeout=task.timeout,
            )

        task._state = TaskState.OPENED
        await self._run_callback(task, task.on_opened())

        return task

    async def close_task(self, task: Task, need_ack: bool | None = None) -> None:
        task = self._running_tasks[task.transaction_id]

        if not (task._state == TaskState.OPENING or task._state == TaskState.CLOSING):
            task._state = TaskState.CLOSING
            need_ack = (need_ack is not None and need_ack) or (
                need_ack is None and task.need_ack
            )

            await self._send_message(
                command=Command.CLOSE_TASK,
                transaction_id=task.transaction_id,
                need_ack=need_ack,
            )
            if need_ack:
                await asyncio.wait_for(
                    task._closed_event.wait(),
                    timeout=task.timeout,
                )
            task._state = TaskState.CLOSED
            self._running_tasks.pop(task.transaction_id)

    async def send_chunk(
        self, task: Task, data: bytes, need_ack: bool | None = None
    ) -> None:
        task = self._running_tasks[task.transaction_id]
        data_id = task._next_data_id
        
        await self._send_message(
            command=Command.DATA_CHUNK,
            transaction_id=task.transaction_id,
            data_id=data_id,
            data=data,
            need_ack=task.need_ack,
        )
        
        need_ack = (need_ack is not None and need_ack) or (
                need_ack is None and task.need_ack
            )

        if not need_ack:
            task._next_data_id += 1
            return

        fut = asyncio.get_running_loop().create_future()
        task._pending_acks[data_id] = fut

        try:
            await asyncio.wait_for(
                fut,
                timeout=task.timeout,
            )
            task._next_data_id += 1

        except TimeoutError:
            task._pending_acks.pop(data_id, None)

            raise TimeoutError(
                f"[Client]no ACK tid={task.transaction_id} data_id={data_id}"
            )

    async def _on_message(self, message: Message) -> None:
        try:
            tid = message.header.transaction_id

            task = self._running_tasks.get(tid)

            if task is None:
                _logger.warning("[CLIENT]unknown tid=%d", tid)
                await self._send_nack(message)
                return

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
        tid = msg.header.transaction_id
        await self._send_message(
            command=Command.NACK,
            transaction_id=tid,
            data_id=(
                msg.payload[NUM_BYTES_OFFSET_DATA_ID_IN_PAYLOAD]
                if msg.header.command == Command.DATA_CHUNK
                else tid
            ),
        )

    async def _handle_ack(
        self,
        task: Task,
        message: Message,
    ) -> None:
        payload = message.payload

        if task.state == TaskState.OPENING:
            task._opened_event.set()
            return

        if task.state == TaskState.CLOSING:
            task._finished_event.set()
            return

        self._validate_payload_has_data_id(payload)
        data_id = payload[NUM_BYTES_OFFSET_DATA_ID_IN_PAYLOAD]

        fut = task._pending_acks.pop(data_id, None)

        if fut is None:
            _logger.warning(
                "[CLIENT]  unexpected ACK tid=%d data_id=%d",
                task.transaction_id,
                data_id,
            )
            return

        if not fut.done():
            fut.set_result(True)

    async def _handle_nack(
        self,
        task: Task,
        message: Message,
    ) -> None:
        payload = message.payload

        self._validate_payload_has_data_id(payload)
        data_id = payload[NUM_BYTES_OFFSET_DATA_ID_IN_PAYLOAD]

        fut = task._pending_acks.pop(data_id, None)

        if fut is None:
            _logger.warning(
                "[CLIENT]  Unexpected NACK tid=%d data_id=%d",
                task.transaction_id,
                data_id,
            )
            return

        if not fut.done():
            _logger.error(
                "[CLIENT]  Unexpected NACK tid=%d data_id=%d",
                task.transaction_id,
                data_id,
            )
            fut.set_exception(ReceivedNackError)

    async def _handle_chunk(
        self,
        task: Task,
        message: Message,
    ) -> None:
        payload = message.payload

        self._validate_payload_has_data_id(payload)

        flags = message.header.flags
        data_id = payload[NUM_BYTES_OFFSET_DATA_ID_IN_PAYLOAD]
        chunk = payload[NUM_BYTES_OFFSET_DATA_ID_IN_PAYLOAD + 1 :]

        task._received_data[data_id] = chunk
        task._state = TaskState.RECEIVED_DATA

        if flags.need_ack:
            await self._send_message(
                command=Command.ACK,
                transaction_id=task.transaction_id,
                data_id=data_id,
            )

        await self._run_callback(task, task.on_data_chunk_received())

    async def _handle_return(
        self,
        task: Task,
        message: Message,
    ) -> None:
        if task.state not in (
            TaskState.OPENED,
            TaskState.RECEIVED_DATA,
        ):
            return

        task._state = TaskState.RETURNED
        task._finished_event.set()

        self._running_tasks.pop(task.transaction_id, None)

        await self._run_callback(task, task.on_data_chunk_received())

    async def _send_message(
        self,
        command: Command,
        transaction_id: int,
        *,
        func_id: int = 0,
        data_id: int = 0,
        data: bytes = b"",
        need_ack: bool = False,
    ) -> None:
        builder = (
            MessageBuilder()
            .set_command(command)
            .set_transaction_id(transaction_id)
            .set_func_id(func_id)
            .set_data_id(data_id)
            .set_data(data)
            .set_need_ack(need_ack)
        )

        message = builder.build()

        await self._device.write(message)

    async def _run_callback(self, task: Task, cb: AsyncIterable[CallbackAction]):
        async for action in cb:
            await self._handle_action(task, action)

    async def _handle_action(self, task: Task, action) -> None:
        match action:
            case SendChunk(data, need_ack):
                await self.send_chunk(task, data, need_ack)
            case CloseTask(need_ack):
                await self.close_task(task,need_ack)
            case _:
                _logger.warning("[CLIENT] unknown action: %s", action)

    def _validate_payload_has_data_id(self, payload: bytes) -> None:
        if len(payload) <= NUM_BYTES_OFFSET_DATA_ID_IN_PAYLOAD:
            raise ValueError("payload too short for data_id")

    def _next_transaction_id(self) -> int:
        used = set(self._running_tasks.keys())

        for tid in range(0, MAX_TRANSACTIONS):
            if tid not in used:
                return tid

        raise RuntimeError(f"[Client]all {MAX_TRANSACTIONS} transaction IDs in use")

    async def _receive_loop(self) -> None:
        self._running = True
        self._receiver_started.set()

        while self._running:
            message = await self._device.read()
            await self._on_message(message)

        self._running = False
