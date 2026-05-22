import asyncio
import logging
from typing import Awaitable, Callable, Dict

from .commands import Command
from .constants import MAX_TRANSACTIONS, NUM_BYTES_OFFSET_DATA_ID_IN_PAYLOAD
from .device_session import DeviceSession
from .message import Message
from .message_builder import MessageBuilder
from .task import Task, TaskState

_logger = logging.getLogger(__name__)


class TaskManager:
    def __init__(self, device: DeviceSession) -> None:
        self._device = device
        self._running_tasks: Dict[int, Task] = {}

    async def open_task(self, task: Task) -> Task:
        tid = self._next_transaction_id()
        task.state = TaskState.OPENING  # type: ignore

        self._running_tasks[tid] = task

        self._device.expect(tid, self._on_message)

        await self._send_message(
            command=Command.OPEN_TASK,
            transaction_id=tid,
            func_id=task.func_id,
            need_ack=task.need_ack,
        )

        if task.need_ack:
            await asyncio.wait_for(
                task._opened_event.wait(),
                timeout=task.timeout,
            )
            
        await task.on_opened()
            
        return task

    async def send_chunk(
        self,
        task: Task,
        data: bytes
    ) -> None:
        task = self._running_tasks[task.transaction_id]
        data_id = task._next_data_id

        if task.need_ack:
            fut = asyncio.get_running_loop().create_future()
            task._pending_acks[data_id] = fut

        await self._send_message(
            command=Command.DATA_CHUNK,
            transaction_id=task.transaction_id,
            data_id=data_id,
            data=data,
            need_ack=task.need_ack,
            is_last=True,
        )

        if not task.need_ack:
            task._next_data_id += 1
            return

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
                return

            handlers: dict[
                Command,
                Callable[
                    [Task, Message],
                    Awaitable[None],
                ],
            ] = {
                Command.ACK: self._handle_ack,
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

        except Exception as e:
            _logger.error("[CLIENT]error handling message: %s", e)
            raise

    async def _handle_ack(
        self,
        task: Task,
        message: Message,
    ) -> None:
        payload = message.payload

        if task.state == TaskState.OPENING:
            task._state = TaskState.OPENED
            task._opened_event.set()
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
        
        task._received_data.extend(chunk)
        task._state = TaskState.RECEIVED_DATA

        if flags.need_ack:
            await self._send_message(
                command=Command.ACK,
                transaction_id=task.transaction_id,
                data_id=data_id,
            )

            await task.on_data_chunk_received()


    async def _handle_return(
        self,
        task: Task,
        message: Message,
    ) -> None:
        if task.state not in (
            TaskState.OPENED,
            TaskState.OPENING,
            TaskState.RECEIVED_DATA,
        ):
            return

        task._state = TaskState.FINISHED
        task._finished_event.set()

        self._running_tasks.pop(task.transaction_id, None)

        if task.on_return is not None:
            await task.on_return()

    async def _send_message(
        self,
        command: Command,
        transaction_id: int,
        *,
        func_id: int = 0,
        data_id: int = 0,
        data: bytes = b"",
        need_ack: bool = False,
        is_last: bool = False,
    ) -> None:
        builder = (
            MessageBuilder()
            .set_command(command)
            .set_transaction_id(transaction_id)
            .set_func_id(func_id)
            .set_data_id(data_id)
            .set_data(data)
            .set_need_ack(need_ack)
            .set_is_last(is_last)
        )

        message = builder.build()

        await self._device.connection.send(message.to_bytes())

    def _validate_payload_has_data_id(self, payload: bytes) -> None:
        if len(payload) <= NUM_BYTES_OFFSET_DATA_ID_IN_PAYLOAD:
            raise ValueError("payload too short for data_id")

    def _next_transaction_id(self) -> int:
        used = set(self._running_tasks.keys())

        for tid in range(0, MAX_TRANSACTIONS):
            if tid not in used:
                return tid

        raise RuntimeError(f"[Client]all {MAX_TRANSACTIONS} transaction IDs in use")
