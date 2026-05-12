import asyncio
import socket
import subprocess
import time

import pytest

from elasticai.experiment_framework.remote_control.pc_side import TaskRegistry
from elasticai.experiment_framework.remote_control.pc_side.basic_usage.main import (
    RemoteTestClient,
)
from elasticai.experiment_framework.remote_control.pc_side.protocol.remote_control_protocol import (
    RemoteControlProtocol,
)
from elasticai.experiment_framework.remote_control.pc_side.protocol.remote_task_controller import (
    RemoteTaskController,
)

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8080

SERVER_BIN = "build/debug/embedded_remote_control"


def wait_for_port(host, port, timeout=5.0):
    start = time.time()

    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=0.1):
                return True
        except OSError:
            time.sleep(0.05)

    return False


@pytest.fixture(scope="session", autouse=True)
def build_server():
    configure = subprocess.run(
        ["cmake", "--preset", "debug"],
        capture_output=True,
        text=True,
    )

    if configure.returncode != 0:
        pytest.fail(f"CMake configure failed:\n{configure.stderr}")

    build = subprocess.run(
        ["cmake", "--build", "--preset", "debug"],
        capture_output=True,
        text=True,
    )

    if build.returncode != 0:
        pytest.fail(f"CMake build failed:\n{build.stderr}")


@pytest.fixture
def c_server(build_server):
    proc = subprocess.Popen(
        [
            SERVER_BIN,
            SERVER_HOST,
            str(SERVER_PORT),
        ],
    )

    if not wait_for_port(SERVER_HOST, SERVER_PORT):
        proc.kill()

        pytest.fail("Server failed to start")

    yield proc

    proc.terminate()

    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()


async def send_message_get(msg: bytes):
    registry = TaskRegistry()

    @registry.task(func_id=0, timeout=5.0)
    async def on_opened(ctx, send):
        await send(msg)

    async def on_inference_chunk(ctx, data):
        print(f"verified result: {data}")

    async def on_inference_done(ctx):
        print(f"all data: {ctx.received_data}")

    async def on_last_chunk(ctx):
        print("The last chunk is received")

    registry.get(0).on_data_chunk_received = on_inference_chunk
    registry.get(0).on_finished = on_inference_done
    registry.get(0).on_is_last = on_last_chunk

    protocol = RemoteControlProtocol()
    session = await protocol.connect_tcp(SERVER_HOST, SERVER_PORT)
    controller = RemoteTaskController(session, registry)

    try:
        (ctx,) = await asyncio.gather(
            controller.open_task(func_id=0),
        )

        await ctx.finished_event.wait()

        return ctx

    finally:
        await protocol.disconnect(session)


@pytest.mark.parametrize("msg", [b"hello"])
@pytest.mark.asyncio
async def test_messages(c_server, msg):
    client = RemoteTestClient(SERVER_HOST, SERVER_PORT)

    ctx, result = await client.run_task(msg)

    assert ctx.is_finished
