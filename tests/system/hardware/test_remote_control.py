import asyncio
import logging
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter_ns
from typing import AsyncGenerator
from unittest.mock import AsyncMock, PropertyMock, patch

import pandas as pd
import pytest
import pytest_asyncio

from elasticai.experiment_framework.remote_control.callback_actions import (
    CallbackAction,
    NoAction,
)
from elasticai.experiment_framework.remote_control.devices import (
    _DeviceSpec,
    probe_for_devices,
)
from elasticai.experiment_framework.remote_control.message_io import (
    MessageIO,
)
from elasticai.experiment_framework.remote_control.task import (
    Task,
    TaskState,
)
from elasticai.experiment_framework.remote_control.task_manager import (
    TaskManager,
)

logging.basicConfig(format="%(message)s")
_logger = logging.getLogger(__name__)

SERIAL_PORT = "/dev/tty/ACM0"
SERIAL_BAUDRATE = 115200

SPECS: set[_DeviceSpec] = {
    _DeviceSpec(10, 11914, "env5"),
}
PICO_USB_ID = "2e8a:0003"

SERVER_CMAKE = "example-firmwares/remote_control"
PICO_BUILD_DIR = Path(SERVER_CMAKE) / "build" / "pico-debug"
PICO_UF2 = PICO_BUILD_DIR / "src" / "app" / "remote_control.uf2"


@pytest.fixture(scope="session", autouse=False)
def build_pico_firmware():
    configure = subprocess.run(
        ["cmake", "--preset", "pico-debug"],
        cwd=SERVER_CMAKE,
        capture_output=True,
        text=True,
    )
    if configure.returncode != 0:
        pytest.fail(f"CMake configure (pico) failed:\n{configure.stderr}")

    build = subprocess.run(
        ["cmake", "--build", "--preset", "pico-debug", "--clean-first"],
        cwd=SERVER_CMAKE,
        capture_output=True,
        text=True,
    )
    if build.returncode != 0:
        pytest.fail(
            f"CMake build (pico) failed\n\nSTDOUT:\n{build.stdout}\n\n"
            f"STDERR:\n{build.stderr}"
        )

    if not PICO_UF2.exists():
        pytest.fail(f"Expected UF2 not found at {PICO_UF2}")


def wait_for_device(timeout=10):
    start = time.time()

    _logger.info("waiting for device")

    while time.time() - start < timeout:
        devices = probe_for_devices(SPECS)
        if devices:
            time.sleep(0.5)
            return devices[0]
        time.sleep(0.5)
    _logger.info("waiting for device 2")

    raise RuntimeError("Pico did not re-enumerate")


@pytest.fixture(scope="session")
def flashed_pico(build_pico_firmware):
    flash = subprocess.run(
        ["picotool", "load", str(PICO_UF2), "-f"],
        # capture_output=True,
        # text=True,
    )

    if flash.returncode != 0:
        pytest.fail(
            "Failed to flash the Pico.\n\n"
            f"stdout:\n{flash.stdout}\n"
            f"stderr:\n{flash.stderr}\n\n"
            "Make sure picotool is installed and the Pico is connected."
        )


class DummyTask(Task):
    def __init__(self, task_def_id: int) -> None:
        super().__init__(task_def_id)

    async def on_opened(self) -> AsyncGenerator[CallbackAction, None]:
        _logger.debug(f"[CLIENT] callback: task openned state = {self.state}")
        yield NoAction()

    async def on_data_chunk_received(self) -> AsyncGenerator[CallbackAction, None]:
        _logger.debug(f"[CLIENT] callback: data chunk received{self.received_data} ")
        yield NoAction()

    async def on_return(self) -> AsyncGenerator[CallbackAction, None]:
        _logger.debug(f"[CLIENT] callback: task returned = {self.state}")
        yield NoAction()


@pytest_asyncio.fixture()
async def manager(flashed_pico):
    subprocess.run(
        ["picotool", "reboot", "-f"],
        capture_output=True,
        text=True,
    )
    device = wait_for_device()

    if not device:
        pytest.skip("No devices found (env5 missing)")

    async with device.connect() as stream:
        manager = TaskManager(MessageIO(stream))
        await manager.start()
        try:
            yield manager
        finally:
            try:
                await manager.stop()
            finally:
                pass


@pytest.mark.hardware
class TestSerialClient:
    @pytest.mark.asyncio
    async def test_round_trip_message(self, manager):
        data = b"abcdefghijkl"

        task = DummyTask(task_def_id=0)

        await manager.open_task(task)
        await manager.send_chunk(task, data)
        await asyncio.sleep(0.1)

        assert task.state == TaskState.RETURNED
        assert task.received_data[0] == data

    @pytest.mark.asyncio
    async def test_adding_need_ack_waits_for_the_ack(self, manager):
        data = b"abcdefghijkl"

        task = DummyTask(task_def_id=0)

        ack_received = asyncio.Event()

        original = manager._handle_ack

        async def delayed_ack(*args, **kwargs):
            ack_received.set()
            await asyncio.sleep(0.5)
            await original(*args, **kwargs)

        mock = AsyncMock(wraps=delayed_ack)
        setattr(manager, "_handle_ack", mock)

        task_open = asyncio.create_task(manager.open_task(task, need_ack=True))

        await ack_received.wait()

        assert task.state == TaskState.OPENING

        await task_open

        assert task.state == TaskState.OPENED

    @pytest.mark.asyncio
    async def test_closing_task(self, manager):
        data = b"abcdefghijkl"

        task = DummyTask(task_def_id=0)
        task.timeout = 0.1

        await manager.open_task(task)
        await manager.send_chunk(task, data)

        await asyncio.sleep(1)

        assert task.state == TaskState.RETURNED

        await manager.close_task(task, need_ack=True)

        assert task.state == TaskState.CLOSED

    @pytest.mark.asyncio
    async def test_remote_retransmits_after_timeout_on_acks(self, manager, monkeypatch):
        data = b"abcdefghijkl"
        task = DummyTask(task_def_id=2)
        task.timeout = 0.1

        count = 3

        async def ignore_twice_before_ack(task, message):
            nonlocal count
            count -= 1

            if count == 0:
                await manager._send_ack(message)

        monkeypatch.setattr(manager, "_handle_chunk", ignore_twice_before_ack)

        await manager.open_task(task)
        await manager.send_chunk(task, data)

        await asyncio.sleep(2)
        assert count == 0

        task.timeout = 0.5

        with patch(
            "elasticai.experiment_framework.remote_control.message.Message.checksum",
            new_callable=PropertyMock,
        ) as checksum_mock:
            checksum_mock.return_value = 0

            original = manager._handle_nack

            manager._handle_nack = AsyncMock(wraps=original)

            open_task_coro = asyncio.create_task(manager.open_task(task, need_ack=True))
            await asyncio.sleep(0.1)

            await open_task_coro

            manager._handle_nack.assert_called()

    @pytest.mark.asyncio
    async def test_init(self, manager, monkeypatch):
        data = b"0"

        task = DummyTask(task_def_id=3)
        task.timeout = 0.1

        await manager.open_task(task)
        await manager.send_chunk(task, data)

        await asyncio.sleep(2)

        assert task.received_data[0] != data

    @pytest.mark.asyncio
    async def test_fpga_off(self, manager, monkeypatch):
        data = b"0"

        task = DummyTask(task_def_id=5)
        task.timeout = 0.1

        await manager.open_task(task)

        await asyncio.sleep(2)

        assert task.state == TaskState.RETURNED

    @pytest.mark.asyncio
    async def test_fpga_on(self, manager, monkeypatch):
        data = b"0"

        task = DummyTask(task_def_id=4)
        task.timeout = 0.1

        await manager.open_task(task)

        await asyncio.sleep(2)

        assert task.state == TaskState.RETURNED

    @pytest.mark.asyncio
    async def test_get_hardware_id(self, manager, monkeypatch):
        data = b"0"

        task = DummyTask(task_def_id=7)
        task.timeout = 0.1

        await manager.open_task(task)

        await asyncio.sleep(1)

        assert task.received_data[0] != data

    # ---------------------Timer-------------------------------

    @pytest.mark.asyncio
    async def test_timer(self, manager, monkeypatch):
        data = b"0"

        task = DummyTask(task_def_id=11)
        task.timeout = 0.1

        await manager.open_task(task)
        await manager.send_chunk(task, data)

        await asyncio.sleep(1)

        assert task.received_data[0] != data

    @pytest.mark.asyncio
    async def test_timer_mirror(self, manager, monkeypatch):
        data = b"Hallo Welt"

        task = DummyTask(task_def_id=12)
        task.timeout = 0.1

        await manager.open_task(task)
        await manager.send_chunk(task, data)

        await asyncio.sleep(1)

        assert task.received_data[0] == data

    @pytest.mark.asyncio
    async def test_timer_fpga_on(self, manager, monkeypatch):
        data = b"0"

        task = DummyTask(task_def_id=13)
        task.timeout = 0.1

        await manager.open_task(task)
        await manager.send_chunk(task, data)

        await asyncio.sleep(1)

        assert task.received_data[0] != data

    # ----------------------Timer with checksum--------------------------

    @pytest.mark.asyncio
    async def test_timer_checksum(self, manager, monkeypatch):
        data = b"0"

        task = DummyTask(task_def_id=11)
        task.timeout = 0.1
        task.has_crx = True

        await manager.open_task(task)
        await manager.send_chunk(task, data)

        await asyncio.sleep(1)

        assert task.received_data[0] != data

    @pytest.mark.asyncio
    async def test_timer_mirror_checksum(self, manager, monkeypatch):
        data = b"Hallo Welt"

        task = DummyTask(task_def_id=12)
        task.timeout = 0.1
        task.has_crx = True

        await manager.open_task(task)
        await manager.send_chunk(task, data)

        await asyncio.sleep(1)

        assert task.received_data[0] == data

    @pytest.mark.asyncio
    async def test_timer_fpga_on_checksum(self, manager, monkeypatch):
        data = b"0"

        task = DummyTask(task_def_id=13)
        task.timeout = 0.1
        task.has_crx = True

        await manager.open_task(task)
        await manager.send_chunk(task, data)

        await asyncio.sleep(1)

        assert task.received_data[0] != data

    # ----------------------Timer with ack/nack--------------------------

    @pytest.mark.asyncio
    async def test_timer_ack(self, manager, monkeypatch):
        data = b"0"

        task = DummyTask(task_def_id=11)
        task.timeout = 0.1
        task.need_ack = True

        await manager.open_task(task)
        await manager.send_chunk(task, data)

        await asyncio.sleep(1)

        assert task.received_data[0] != data

    @pytest.mark.asyncio
    async def test_timer_mirror_ack(self, manager, monkeypatch):
        data = b"Hallo Welt"

        task = DummyTask(task_def_id=12)
        task.timeout = 0.1
        task.need_ack = True

        await manager.open_task(task)
        await manager.send_chunk(task, data)

        await asyncio.sleep(1)

        assert task.received_data[0] == data

    @pytest.mark.asyncio
    async def test_timer_fpga_on_ack(self, manager, monkeypatch):
        data = b"0"

        task = DummyTask(task_def_id=13)
        task.timeout = 0.1
        task.need_ack = True

        await manager.open_task(task)
        await manager.send_chunk(task, data)

        await asyncio.sleep(1)

        assert task.received_data[0] != data

    # ----------------------Timer with ack + checksum--------------------------

    @pytest.mark.asyncio
    async def test_timer_ack_checksum(self, manager, monkeypatch):
        data = b"0"

        task = DummyTask(task_def_id=11)
        task.timeout = 0.1
        task.need_ack = True
        task.has_crx = True

        await manager.open_task(task)
        await manager.send_chunk(task, data)

        await asyncio.sleep(1)

        assert task.received_data[0] != data

    @pytest.mark.asyncio
    async def test_timer_mirror_ack_checksum(self, manager, monkeypatch):
        data = b"Hallo Welt"

        task = DummyTask(task_def_id=12)
        task.timeout = 0.1
        task.need_ack = True
        task.has_crx = True
        await manager.open_task(task)
        await manager.send_chunk(task, data)

        await asyncio.sleep(1)

        assert task.received_data[0] == data

    @pytest.mark.asyncio
    async def test_timer_fpga_on_ack_checksum(self, manager, monkeypatch):
        data = b"0"

        task = DummyTask(task_def_id=13)
        task.timeout = 0.1
        task.need_ack = True
        task.has_crx = True

        await manager.open_task(task)
        await manager.send_chunk(task, data)

        await asyncio.sleep(1)

        assert task.received_data[0] != data


@dataclass(frozen=True)
class TransmissionConfig:
    name: str
    need_ack: bool
    need_checksum: bool


TRANSMISSION_CONFIGS = (
    TransmissionConfig(
        name="none",
        need_ack=False,
        need_checksum=False,
    ),
    TransmissionConfig(
        name="ack",
        need_ack=True,
        need_checksum=False,
    ),
    TransmissionConfig(
        name="checksum",
        need_ack=False,
        need_checksum=True,
    ),
    TransmissionConfig(
        name="ack+checksum",
        need_ack=True,
        need_checksum=True,
    ),
)


class TransmissionTask(Task):
    def __init__(self, task_def_id: int) -> None:
        super().__init__(task_def_id)
        self.data_received = asyncio.Event()

    async def on_opened(self):
        yield NoAction()

    async def on_data_chunk_received(self):
        self.data_received.set()
        yield NoAction()

    async def on_return(self):
        yield NoAction()


class TestTransmissionTime:
    PAYLOAD_SIZES = [128, 256, 512, 1024, 2048]
    ITERATIONS = 500

    output_path = Path("benchmark/data/transmission_benchmark.csv")
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    async def run_transmission_benchmark(
        self,
        manager,
        config: TransmissionConfig,
    ):
        previous_disable = logging.root.manager.disable
        #logging.disable(logging.CRITICAL)

        try:
            task = TransmissionTask(task_def_id=16)

            # The task controls whether outgoing messages contain CRC.
            task.need_ack = config.need_ack
            task.has_crx = config.need_checksum

            await manager.open_task(task)

            results = []

            # -------------------------------------------------
            # Warm-up
            # -------------------------------------------------
            for size in self.PAYLOAD_SIZES:
                data = bytes(size)

                for _ in range(20):
                    task.data_received.clear()

                    await manager.send_chunk(
                        task,
                        data,
                        need_ack=config.need_ack,
                    )

                    await task.data_received.wait()

            # -------------------------------------------------
            # Measurements
            # -------------------------------------------------
            for size in self.PAYLOAD_SIZES:
                data = bytes(size)

                for iteration in range(self.ITERATIONS):
                    task.data_received.clear()

                    start = perf_counter_ns()

                    await manager.send_chunk(
                        task,
                        data,
                        need_ack=config.need_ack,
                    )

                    await task.data_received.wait()

                    elapsed_ns = perf_counter_ns() - start

                    results.append(
                        {
                            "configuration": config.name,
                            "need_ack": config.need_ack,
                            "need_checksum": config.need_checksum,
                            "payload_size": size,
                            "iteration": iteration,
                            "time_ns": elapsed_ns,
                            "time_us": elapsed_ns / 1_000,
                        }
                    )

            await manager.close_task(task)

            return results

        finally:...
           # logging.disable(previous_disable)

    @pytest.mark.asyncio
    async def test_transmission_benchmark(
        self,
        manager,
    ):
        results = []

        for config in TRANSMISSION_CONFIGS:
            config_results = await self.run_transmission_benchmark(
                manager,
                config,
            )

            results.extend(config_results)

        df = pd.DataFrame(results)

        df.to_csv(
            self.output_path,
            index=False,
        )
