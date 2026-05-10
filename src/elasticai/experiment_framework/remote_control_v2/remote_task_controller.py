# remote_task_controller.py
import asyncio
import logging
from operator import ne
from sys import flags
from typing import Dict, Optional

from elasticai.experiment_framework.remote_control_v2.message import Message
from elasticai.experiment_framework.remote_control_v2.message_builder import MessageBuilder

from .commands       import Command
from .flags          import Flags
from .task_context   import TaskContext
from .task_definition import TaskDefinition
from .task_registry  import TaskRegistry
from .device_session import DeviceSession
from .constants      import MAX_TRANSACTIONS, NUM_BYTES_OFFSET_DATA_ID_IN_PAYLOAD

class RemoteTaskController:

    def __init__(self, device: DeviceSession, registry: TaskRegistry) -> None:
        self._device   = device
        self._registry = registry
        self._logger   = logging.getLogger(__name__)

        self._tasks: Dict[int, tuple[TaskContext, TaskDefinition]] = {}


    async def open_task(self, func_id: int) -> TaskContext:
        definition = self._registry.get(func_id)
        tid        = self._next_transaction_id()
        ctx        = TaskContext(transaction_id=tid)
        need_ack = definition.need_ack

        self._tasks[tid] = (ctx, definition)
        self._device.expect(tid, lambda msg: asyncio.create_task(self._on_message(msg)))

        print(f"[open_task] func_id={func_id} tid={tid} need_ack={need_ack}")

        msg = next(
            MessageBuilder()
                .set_command(Command.OPEN_TASK)
                .set_transaction_id(tid)
                .set_func_id(func_id)
                .set_need_ack(need_ack)
                .build()
        )
        await self._device.connection.send(msg.to_bytes())

        if need_ack: 
            print(f"[open_task] waiting for opened_event tid={tid}")
            await asyncio.wait_for(ctx.opened_event.wait(), timeout=definition.timeout)
            print(f"[open_task] task opened tid={tid}")
        
        if (on_opened := definition.on_opened) is not None:
                    async def send(data: bytes) -> None:
                        await self.send_chunk(ctx, data)
                    await on_opened(ctx, send)
        return ctx


    async def send_chunk(self, ctx: TaskContext, data: bytes) -> None:
        _, definition = self._tasks[ctx.transaction_id]
        need_ack      = definition.need_ack
        data_id       = ctx.next_data_id

        print(f"[send_chunk] tid={ctx.transaction_id} data_id={data_id} len={len(data)} need_ack={need_ack}")

        if need_ack:
            fut = asyncio.get_running_loop().create_future()
            ctx._pending_acks[data_id] = fut

        msg = next(
            MessageBuilder()
                .set_command(Command.DATA_CHUNK)
                .set_transaction_id(ctx.transaction_id)
                .set_data_id(data_id)
                .set_data(data)
                .set_need_ack(need_ack)
                .build()
        )
        ctx.next_data_id += 1
        await self._device.connection.send(msg.to_bytes())
        print(f"[send_chunk] sent tid={ctx.transaction_id} data_id={data_id}")

        if need_ack:
            print(f"[send_chunk] waiting for ACK tid={ctx.transaction_id} data_id={data_id}")
            await asyncio.wait_for(fut, timeout=definition.timeout)
            print(f"[send_chunk] ACK received tid={ctx.transaction_id} data_id={data_id}")


    async def _on_message(self, message: Message) -> None:
        try:
            print(f"[_on_message] message= {message}")

            flags = message.header.flags
            tid = message.header.transaction_id
            payload = message.payload
            cmd = message.header.command

            print(f"[_on_message] cmd={cmd} tid={tid}")

            entry = self._tasks.get(tid)
            if entry is None:
                print(f"[_on_message] unknown tid={tid} — dropping")
                self._logger.warning("unknown tid=%d", tid)
                return

            ctx, definition = entry
            if cmd == Command.ACK:
                if  ctx.state == "opening":
                    print(f"[_on_message] RETURN → task opened tid={tid}")
                    ctx.state = "opened"
                    ctx.opened_event.set()
                    return

                data_id = payload[NUM_BYTES_OFFSET_DATA_ID_IN_PAYLOAD]
                print(f"[_on_message] ACK tid={tid} data_id={data_id}")
                fut = ctx._pending_acks.pop(data_id, None)
                if fut and not fut.done():
                    fut.set_result(True)
                    print(f"[_on_message] ACK resolved future tid={tid} data_id={data_id}")
                else:
                    print(f"[_on_message] unexpected ACK tid={tid} data_id={data_id}")
                    self._logger.warning("unexpected ACK tid=%d data_id=%d", tid, data_id)
                return

            if cmd == Command.DATA_CHUNK:
                data_id = payload[NUM_BYTES_OFFSET_DATA_ID_IN_PAYLOAD]
                chunk   = payload[NUM_BYTES_OFFSET_DATA_ID_IN_PAYLOAD:]
                print(f"[_on_message] DATA_CHUNK tid={tid} data_id={data_id} len={len(chunk)}: {chunk.hex()}")

                ctx.received_data.extend(chunk)
                ctx.state = "received_data"

                if flags.need_ack:
                    print(f"[_on_message] sending ACK tid={tid} data_id={data_id}")
                    ack = next(
                        MessageBuilder()
                            .set_command(Command.ACK)
                            .set_transaction_id(tid)
                            .set_data_id(data_id)
                            .build()
                    )
                    await self._device.connection.send(ack.to_bytes())

                if (on_data_chunk := definition.on_data_chunk_received) is not None:
                    await on_data_chunk(ctx, chunk)
                return

            if cmd == Command.RETURN and ctx.state in ("opened", "received_data"):
                print(f"[_on_message] RETURN → task finished tid={tid}")
                ctx.state = "finished"
                ctx.finished_event.set()
                self._tasks.pop(tid)

                if (on_finished := definition.on_finished) is not None:
                    await on_finished(ctx)

        except Exception as e:
            print(f"[_on_message] ERROR: {e}")
            self._logger.error("error handling message: %s", e)
            raise
        
    def _next_transaction_id(self) -> int:
        used = set(self._tasks.keys())
        for tid in range(1, MAX_TRANSACTIONS):
            if tid not in used:
                return tid
        raise RuntimeError(f"all {MAX_TRANSACTIONS} transaction IDs in use")