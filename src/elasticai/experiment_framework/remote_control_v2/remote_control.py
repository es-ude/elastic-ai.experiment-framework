import contextlib
from collections.abc import Generator
import logging
import click
from typing import Optional

from .io_stream import IOStream
from .message import Message
from .commands import Command
from .remote_control_protocol import RemoteControlProtocol
from .remote_task_controller import TaskContext
from .socket_io_stream import SocketIOStream


@contextlib.contextmanager
def connect(host: str, port: int) -> Generator[IOStream]:
    stream = SocketIOStream(host, port)
    with stream.connect() as io_stream:
        yield io_stream


class RemoteControl:
    def __init__(self, device: IOStream):
        self._rcp = RemoteControlProtocol(device)

    def echo(self, data: bytes) -> bytes:
        return self._rcp.echo(data)

    def send_command(self, command: Command, data: bytes = b"") -> Message:
        return self._rcp.send_command(command, data)

    def start_receive_loop(self) -> None:
        self._rcp.start_receive_loop()

    def stop_receive_loop(self) -> None:
        self._rcp.stop_receive_loop()

    def call_function(self, func_id: int, args: bytes = b"") -> bytes:
        return self._rcp.call_function(func_id, args)

    def open_task(self, func_id: int, payload: bytes = b"") -> TaskContext:
        return self._rcp.open_task(func_id, payload)

    def send_data_chunk(self, text: bytes = b"") -> int:
        return self._rcp.send_data_chunk(text)

    def expect_response_text(self, expected: bytes) -> None:
        self._rcp.expect_response_text(expected)

    def process_next_message(self) -> Optional[TaskContext]:
        return self._rcp.process_next_message()

    @property
    def active_context(self) -> Optional[TaskContext]:
        return self._rcp.active_context


@click.group()
@click.option("--host", default="localhost", type=str)
@click.option("--port", default=8080,       type=int)
@click.option("--verbose", "-v",            is_flag=True)
@click.pass_context
def main(ctx, host, port, verbose):
    """Interact with elastic-ai hardware over TCP socket."""
    if verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s %(levelname)s %(name)s:%(lineno)d: %(message)s",
            datefmt="%H:%M:%S",
        )
    ctx.obj = ctx.with_resource(connect(host, port))


@main.command
@click.pass_obj
@click.argument("data", type=str)
def echo(obj, data: str):
    """Send two bytes and verify echo. Data as hex e.g. 'AABB'"""
    rc      = RemoteControl(obj)
    payload = bytes.fromhex(data)
    result  = rc.echo(payload)

    if result == payload:
        print(f"✅ Echo OK: {result.hex()}")
    else:
        print(f"❌ Echo FAILED!")
        print(f"   Sent:     {payload.hex()}")
        print(f"   Received: {result.hex()}")


@main.command
@click.pass_obj
@click.argument("cmd_id", type=int)
@click.argument("data",   type=str)
def send(obj, cmd_id: int, data: str):
    """Send a raw command. cmd_id as int, data as hex."""
    rc       = RemoteControl(obj)
    payload  = bytes.fromhex(data)
    response = rc.send_command(Command(cmd_id), payload)
    print(f"Response: {response.payload.hex()}")


@main.command
@click.pass_obj
@click.argument("func_id", type=int)
@click.argument("args", type=str, default="")
def call(obj, func_id: int, args: str):
    """Call a remote function using OPEN_TASK/DATA_CHUNK flow."""
    rc = RemoteControl(obj)
    payload = bytes.fromhex(args) if args else b""
    result = rc.call_function(func_id, payload)
    print(f"Function {func_id} result: {result.hex()}")