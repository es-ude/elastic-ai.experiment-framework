import logging
import os
import signal
import socket
import subprocess
import time

import pytest

from elasticai.experiment_framework.remote_control.pc_side.basic_usage.main import (
    RemoteTestClient,
)
from elasticai.experiment_framework.remote_control.pc_side.protocol.task_context import (
    TaskState,
)

logging.basicConfig(format="%(message)s")
logger = logging.getLogger(__name__)


SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8080

SERVER_BIN = "build/debug/embedded_remote_control"


def wait_for_port(host, port, timeout=10.0):
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
    try:
        result = subprocess.run(
            ["lsof", "-i", f":{SERVER_PORT}"],
            capture_output=True,
            text=True,
        )
        if result.stdout:
            lines = result.stdout.split("\n")[1:]  # skip header
            for line in lines:
                if line.strip():
                    pid = int(line.split()[1])
                    os.kill(pid, signal.SIGKILL)
                    time.sleep(0.1)
    except Exception:
        pass

    proc = subprocess.Popen([SERVER_BIN, SERVER_HOST, str(SERVER_PORT)])

    if not wait_for_port(SERVER_HOST, SERVER_PORT):
        proc.kill()

        pytest.fail("Server failed to start")

    yield proc

    proc.terminate()

    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.mark.parametrize("msg", [b"hello"])
@pytest.mark.asyncio
async def test_messages(c_server, msg):
    client = RemoteTestClient(SERVER_HOST, SERVER_PORT)

    ctx, result = await client.run_task(msg)

    assert ctx.state == TaskState.FINISHED
