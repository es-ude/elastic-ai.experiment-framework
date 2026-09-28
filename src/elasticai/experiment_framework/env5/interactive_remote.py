import asyncio
import atexit
import csv
import logging
import readline
import shlex
import struct
from collections.abc import Iterator
from pathlib import Path

import click

from elasticai.experiment_framework.remote_control import (
    Command,
    Flags,
    Message,
    SyncRemoteControl,
)
from elasticai.experiment_framework.remote_control.devices import (
    _SerialDevice,
)

from ..remote_control.logging_config import configure_logging
from .flash_env5 import flashed_pico, wait_for_device
from .tasks_registry import SimpleTask

HISTORY_FILE = Path.home() / ".local" / "state" / "eaixp" / "remote-history"


class GenericRemoteControl(SyncRemoteControl):
    """Generic synchronous interface to the remote-control protocol."""

    def __init__(self, device):
        super().__init__(device)
        self.running_tasks: dict[int, SimpleTask] = dict()

    def open_task(
        self,
        task_def_id: int,
        need_ack: bool = False,
        has_crc: bool = False,
    ) -> None:
        task = SimpleTask(
            task_def_id=task_def_id,
            need_ack=need_ack,
            has_crc=has_crc,
        )

        try:
            self._loop.run_until_complete(
                self._manager.open_task(task, need_ack=need_ack)
            )
            self.running_tasks[task.task_id] = task
        except Exception:
            self.running_tasks = None
            raise

    def send_chunk(
        self,
        task_id: int,
        data: bytes,
        need_ack: bool | None = None,
    ) -> None:

        task = self.running_tasks.get(task_id, None)
        if task is None:
            raise RuntimeError(f"No task of id= {task_id} is open.")

        self._run_then_delay(
            self._manager.send_chunk(
                task,
                data,
                need_ack=need_ack,
            )
        )

    def send_file(
        self,
        task_id: int,
        path: Path,
        chunk_size: int = 256,
        need_ack: bool | None = None,
    ) -> None:

        task = self.running_tasks.get(task_id, None)
        if task is None:
            raise RuntimeError(f"No task of id= {task_id} is open.")

        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero.")

        chunk = bytearray()

        for data in self._csv_to_binary_chunks(path):
            chunk.extend(data)

            while len(chunk) >= chunk_size:
                data_to_send = bytes(chunk[:chunk_size])
                del chunk[:chunk_size]

                self._run_then_delay(
                    self._manager.send_chunk(
                        task,
                        data_to_send,
                        need_ack=need_ack,
                    )
                )

        if len(chunk) > 0 and len(chunk) < chunk_size:
            self._loop.run_until_complete(
                self._manager.send_chunk(
                    task,
                    bytes(chunk),
                    need_ack=need_ack,
                )
            )

    def send_invalid_message(self, task_id: int, data):
        task = self.running_tasks.get(task_id, None)
        if task is None:
            raise RuntimeError(f"No task of id= {task_id} is open.")

        task.has_crc = True
        msg = Message(
            Command.DATA_CHUNK,
            data,
            flags=Flags(True, True).to_number(),
            task_id=task_id,
            msg_id=task._next_msg_id,
        )
        corrupted_msg_bytes = msg.to_bytes()[:-1] + bytes([msg.to_bytes()[-1] ^ 0xFF])

        self._run_then_delay(self._manager._device._stream.write(corrupted_msg_bytes))

    def close_task(self, task_id: int) -> None:
        task = self.running_tasks.get(task_id, None)
        if task is None:
            raise RuntimeError(f"No task of id= {task_id} is open.")

        self._run_then_delay(self._manager.close_task(task))
        self.running_tasks.pop(task_id, None)

    def _run_then_delay(self, coro, delay: float = 0.1):
        async def wrapper():
            await coro
            await asyncio.sleep(delay)

        self._loop.run_until_complete(wrapper())

    def _csv_to_binary_chunks(self, path: Path) -> Iterator[bytes]:
        with path.open("r", newline="") as file:
            reader = csv.reader(file)

            for line_number, row in enumerate(reader, start=1):
                if not row:
                    continue

                try:
                    data = [int(value) for value in row]
                except ValueError as exc:
                    raise ValueError(
                        f"{path}:{line_number}: invalid data: {row}"
                    ) from exc

                format_string = f"<{len(data)}B"
                yield struct.pack(format_string, *data)


def parse_flags(args: list[str]) -> tuple[bool, bool]:
    """Parse --ack/--need-ack and --crc from interactive shell arguments."""

    need_ack = False
    has_crc = False

    for arg in args:
        if arg in {"--ack", "--need-ack"}:
            need_ack = True
        elif arg == "--crc":
            has_crc = True
        else:
            raise ValueError(f"Unknown option: {arg}")

    return need_ack, has_crc


def execute_command(
    control: GenericRemoteControl,
    line: str,
) -> bool:
    """
    Execute one interactive command.

    Returns False when the shell should exit.
    """

    args = shlex.split(line)

    if not args:
        return True

    command = args[0]
    args = args[1:]

    if command in {"exit", "quit"}:
        return False

    if command == "help":
        click.echo(
            """
                Commands:

                open TASK_Def_ID [--ack] [--crc]
                    Open a remote task.

                send TASK_ID HEX [--ack]
                    Send raw hexadecimal bytes.
                    
                send-invalid TASK_ID HEX [--ack]
                    Send invalid message with checksum 00 with ack hexadecimal bytes.

                send-file TASK_ID FILE [--chunk-size N] [--ack]
                    Send a binary file in chunks.
                    

                close
                    Close TASK_ID the currently open task.

                status
                    Show the currently open task.

                help
                    Show this help.

                exit
                    Exit the shell.

                    Examples:

                    open 5
                    open 5 --ack --crc
                    send 0 01020304
                    send 2 deadbeef --ack
                    send-file 2 firmware.bin --chunk-size 256
                    close
                    """.strip()
        )
        return True

    if command == "open":
        if not args:
            raise ValueError("Usage: open TASK_ID [--ack] [--crc]")

        task_id = int(args[0], 0)
        need_ack, has_crc = parse_flags(args[1:])

        control.open_task(
            task_def_id=task_id,
            need_ack=need_ack,
            has_crc=has_crc,
        )

        click.echo(f"Opened task {task_id} (ack={need_ack}, crc={has_crc})")
        return True

    if command == "send":
        if not args:
            raise ValueError("Usage: send TASK_ID HEX [--ack]")

        task_id = int(args[0], 0)
        hex_data = args[1].removeprefix("0x")

        try:
            data = bytes.fromhex(hex_data)
        except ValueError as exc:
            raise ValueError(f"Invalid hexadecimal data: {exc}") from exc

        need_ack, has_crc = parse_flags(args[2:])

        # CRC is a task property in the current API.
        if has_crc:
            raise ValueError(
                "Changing CRC with 'send' is not supported after "
                "the task was opened. Open the task with --crc."
            )

        control.send_chunk(
            task_id,
            data,
            need_ack=need_ack,
        )

        click.echo(f"Sent {len(data)} byte(s).")
        return True

    if command == "send-invalid":
        if not args:
            raise ValueError("Usage: send TASK_ID data [--ack]")

        task_id = int(args[0], 0)
        hex_data = args[1].removeprefix("0x")

        try:
            data = bytes.fromhex(hex_data)
        except ValueError as exc:
            raise ValueError(f"Invalid hexadecimal data: {exc}") from exc

        control.send_invalid_message(
            task_id,
            data,
        )

        click.echo(f"Sent {len(data)} with checksum 00 and ack byte(s).")
        return True

    if command == "send-file":
        if not args:
            raise ValueError("Usage: send-file task_id FILE [--chunk-size N] [--ack]")

        task_id = int(args[0], 0)
        path = Path(args[1])

        if not path.is_file():
            raise ValueError(f"File does not exist: {path}")

        chunk_size = 256
        need_ack = False

        i = 2
        while i < len(args):
            arg = args[i]

            if arg == "--ack":
                need_ack = True
                i += 1
                continue

            if arg == "--chunk-size":
                if i + 1 >= len(args):
                    raise ValueError("--chunk-size requires a value.")

                chunk_size = int(args[i + 1])

                if chunk_size <= 0:
                    raise ValueError("--chunk-size must be greater than zero.")

                i += 2
                continue

            raise ValueError(f"Unknown option: {arg}")

        control.send_file(
            task_id,
            path=path,
            chunk_size=chunk_size,
            need_ack=need_ack,
        )

        click.echo(f"Sent file: {path}")
        return True

    if command == "close":
        task_id = int(args[0], 0)
        control.close_task(task_id)
        click.echo(f"Task with id = {task_id} closed.")
        return True

    if command == "status":
        tasks = control.running_tasks

        for task in tasks.values():
            click.echo(
                f"Task def: id={task.task_def_id}, "
                f"Task open: id={task.task_id}, "
                f"need_ack={task.need_ack}, "
                f"has_crc={task.has_crc}"
            )

        return True

    raise ValueError(f"Unknown command: {command}")


def setup_readline() -> None:
    readline.parse_and_bind("set editing-mode emacs")
    readline.parse_and_bind('"\\e[A": previous-history')
    readline.parse_and_bind('"\\e[B": next-history')

    readline.set_history_length(1000)

    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    try:
        readline.read_history_file(HISTORY_FILE)
    except FileNotFoundError:
        pass

    atexit.register(readline.write_history_file, HISTORY_FILE)


def run_shell(control):
    setup_readline()

    while True:
        try:
            line = input(
                "remote>",
            )
        except (EOFError, KeyboardInterrupt):
            click.echo()
            break

        try:
            if not execute_command(control, line):
                break
        except (ValueError, RuntimeError) as exc:
            click.echo(f"Error: {exc}", err=True)
        except Exception as exc:
            click.echo(f"Protocol error: {exc}", err=True)


@click.group()
def remote() -> None:
    """Generic remote-control CLI."""


@remote.command("flash")
@click.option("--debug", is_flag=True)
def flash_command(debug):
    configure_logging(
        level=logging.DEBUG if debug else logging.INFO,
    )

    flashed_pico()
    click.echo("Env5 Flashed Successfully")


@remote.command("shell")
@click.option("--debug", is_flag=True)
@click.option("--raw", "show_raw", is_flag=True)
@click.option("-p", "--port", default="auto")
def shell_command(port, debug, show_raw):
    configure_logging(
        level=logging.DEBUG if debug else logging.INFO,
        show_raw=show_raw,
    )

    if port == "auto":
        device = wait_for_device()
    else:
        device = _SerialDevice(port)

    with device.connect_sync() as stream:
        with GenericRemoteControl(stream) as control:
            run_shell(control)
