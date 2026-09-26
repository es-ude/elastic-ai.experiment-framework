from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter_ns

import pandas as pd
import pytest

from elasticai.experiment_framework.remote_control.callback_actions import (
    SendChunk,
)
from elasticai.experiment_framework.remote_control.io_stream import IOStream
from elasticai.experiment_framework.remote_control.sync_remote_control import (
    SyncRemoteControl,
)
from elasticai.experiment_framework.remote_control.task import Task

output_path = Path("tests/fpga/benchmark/data/remote_task_benchmark.csv")
output_path.parent.mkdir(parents=True, exist_ok=True)

BYTE_STREAM_PATH = Path("tests/fpga/env5_top_reconfig.bin")

# C task IDs
FPGA_POWER_ON_TASK_ID = 16
ECHO_TASK_ID = 17
PREDICT_TASK_ID = 18
WRITE_TO_FLASH_TASK_ID = 19
READ_SKELETON_ID_TASK_ID = 20

# C benchmark task IDs
BENCHMARK_FPGA_POWER_ON_TASK_ID = 21
BENCHMARK_ECHO_TASK_ID = 22
BENCHMARK_PREDICT_TASK_ID = 23
BENCHMARK_WRITE_TO_FLASH_TASK_ID = 24
BENCHMARK_READ_SKELETON_ID_TASK_ID = 25

CHUNK_SIZE = 512

PREDICT_DATA = bytes([1, 0])


# ============================================================================
# Communication configurations
# ============================================================================


@dataclass(frozen=True)
class CommunicationConfig:
    name: str
    need_ack: bool
    need_checksum: bool


COMMUNICATION_CONFIGS = (
    CommunicationConfig(
        name="none",
        need_ack=False,
        need_checksum=False,
    ),
    CommunicationConfig(
        name="ack",
        need_ack=True,
        need_checksum=False,
    ),
    CommunicationConfig(
        name="checksum",
        need_ack=False,
        need_checksum=True,
    ),
    CommunicationConfig(
        name="ack+checksum",
        need_ack=True,
        need_checksum=True,
    ),
)


# ============================================================================
# Remote tasks
# ============================================================================


class FPGA_powerOnTask(Task):
    def __init__(
        self,
        task_def_id: int,
        need_ack: bool,
        need_checksum: bool,
    ) -> None:
        super().__init__(task_def_id)
        self.need_ack = need_ack
        self.has_crx = need_checksum
        self.timeout = 120


class EchoTask(Task):
    def __init__(
        self,
        task_def_id: int,
        data: bytes,
        need_ack: bool,
        need_checksum: bool,
    ) -> None:
        super().__init__(task_def_id)

        self._data = data
        self.need_ack = need_ack
        self.has_crx = need_checksum

    async def on_opened(self):
        yield SendChunk(
            self._data,
            need_ack=self.need_ack,
        )

    @property
    def result(self) -> bytes:
        result = bytearray()

        for _, chunk in sorted(self.received_data.items()):
            result.extend(chunk)

        return bytes(result)


class PredictTask(Task):
    def __init__(
        self,
        task_def_id: int,
        data: bytes,
        need_ack: bool,
        need_checksum: bool,
    ) -> None:
        super().__init__(task_def_id)

        self._data = data
        self.need_ack = need_ack
        self.has_crx = need_checksum

    async def on_opened(self):
        yield SendChunk(
            self._data,
            need_ack=self.need_ack,
        )

    @property
    def result(self) -> bytes:
        result = bytearray()

        for _, chunk in sorted(self.received_data.items()):
            result.extend(chunk)

        return bytes(result)


class WriteToFlashTask(Task):
    def __init__(
        self,
        task_def_id: int,
        sector: int,
        data: bytes,
        chunk_size: int,
        need_ack: bool,
        need_checksum: bool,
    ) -> None:
        super().__init__(task_def_id)

        self._data = data
        self.sector = sector
        self.chunk_size = chunk_size
        self.need_ack = need_ack
        self.need_checksum = need_checksum
        self.has_crx = need_checksum
        self.timeout = 120

    async def on_opened(self):
        yield SendChunk(
            int.to_bytes(
                self.sector,
                length=1,
                byteorder="little",
            ),
            need_ack=self.need_ack,
        )

        for pos in range(0, len(self._data), self.chunk_size):
            chunk = self._data[pos : pos + self.chunk_size]

            yield SendChunk(
                chunk,
                need_ack=self.need_ack,
            )


class ReadSkeletonIdTask(Task):
    def __init__(
        self,
        task_def_id: int,
        need_ack: bool,
        need_checksum: bool,
    ) -> None:
        super().__init__(task_def_id)

        self.need_ack = need_ack
        self.has_crx = need_checksum

    @property
    def result(self) -> bytes:
        result = bytearray()

        for _, chunk in sorted(self.received_data.items()):
            result.extend(chunk)

        return bytes(result)


# ============================================================================
# Benchmark tasks
# ============================================================================


class BenchmarkFPGA_powerOnTask(Task):
    CORE_TIME_DATA_ID = 0

    def __init__(
        self,
        task_def_id: int,
        need_ack: bool,
        need_checksum: bool,
    ) -> None:
        super().__init__(task_def_id)

        self.need_ack = need_ack
        self.has_crx = need_checksum
        self.timeout = 120

    @property
    def core_time_us(self) -> int:
        return int.from_bytes(
            self.received_data[self.CORE_TIME_DATA_ID],
            byteorder="little",
        )


class BenchmarkEchoTask(Task):
    CORE_TIME_DATA_ID = 0
    RESULT_DATA_ID = 1

    def __init__(
        self,
        task_def_id: int,
        data: bytes,
        need_ack: bool,
        need_checksum: bool,
    ) -> None:
        super().__init__(task_def_id)

        self._data = data
        self.need_ack = need_ack
        self.has_crx = need_checksum

    async def on_opened(self):
        yield SendChunk(
            self._data,
            need_ack=self.need_ack,
        )

    @property
    def core_time_us(self) -> int:
        return int.from_bytes(
            self.received_data[self.CORE_TIME_DATA_ID],
            byteorder="little",
        )

    @property
    def result(self) -> bytes:
        return self.received_data[self.RESULT_DATA_ID]


class BenchmarkPredictTask(Task):
    CORE_TIME_DATA_ID = 0
    RESULT_DATA_ID = 1

    def __init__(
        self,
        task_def_id: int,
        data: bytes,
        need_ack: bool,
        need_checksum: bool,
    ) -> None:
        super().__init__(task_def_id)

        self._data = data
        self.need_ack = need_ack
        self.has_crx = need_checksum

    async def on_opened(self):
        yield SendChunk(
            self._data,
            need_ack=self.need_ack,
        )

    @property
    def core_time_us(self) -> int:
        return int.from_bytes(
            self.received_data[self.CORE_TIME_DATA_ID],
            byteorder="little",
        )

    @property
    def result(self) -> bytes:
        return self.received_data[self.RESULT_DATA_ID]


class BenchmarkWriteToFlashTask(Task):
    CORE_TIME_DATA_ID = 0

    def __init__(
        self,
        task_def_id: int,
        sector: int,
        need_ack: bool,
        need_checksum: bool,
    ) -> None:
        super().__init__(task_def_id)

        self.sector = sector
        self.need_ack = need_ack
        self.has_crx = need_checksum
        self.timeout = 3600

    async def on_opened(self):
        yield SendChunk(
            int.to_bytes(
                self.sector,
                length=1,
                byteorder="little",
            ),
            need_ack=self.need_ack,
        )

    @property
    def core_time_us(self) -> int:
        return int.from_bytes(
            self.received_data[self.CORE_TIME_DATA_ID],
            byteorder="little",
        )


class BenchmarkReadSkeletonIdTask(Task):
    CORE_TIME_DATA_ID = 0
    RESULT_DATA_ID = 1

    def __init__(
        self,
        task_def_id: int,
        need_ack: bool,
        need_checksum: bool,
    ) -> None:
        super().__init__(task_def_id)

        self.need_ack = need_ack
        self.has_crx = need_checksum

    @property
    def core_time_us(self) -> int:
        return int.from_bytes(
            self.received_data[self.CORE_TIME_DATA_ID],
            byteorder="little",
        )

    @property
    def result(self) -> bytes:
        return self.received_data[self.RESULT_DATA_ID]


# ============================================================================
# Task registry
# ============================================================================


TaskFactory = Callable[[CommunicationConfig], Task]


@dataclass(frozen=True)
class TaskDefinition:
    task: TaskFactory
    benchmark_task: TaskFactory


@dataclass(frozen=True)
class TaskMeasurement:
    task: str
    configuration: str
    need_ack: bool
    need_checksum: bool
    iteration: int
    remote_time_ns: int
    core_time_us: int

    @property
    def remote_time_us(self) -> float:
        return self.remote_time_ns / 1_000.0

    @property
    def overhead_us(self) -> float:
        return self.remote_time_us - self.core_time_us


class FPGARemoteControl(SyncRemoteControl):
    def __init__(
        self,
        device: IOStream,
        *,
        echo_data: bytes,
        predict_data: bytes,
        flash_data: bytes,
        flash_sector: int = 0,
        chunk_size: int = CHUNK_SIZE,
    ) -> None:
        super().__init__(device)

        self._tasks: dict[str, TaskDefinition] = {}

        self._register_tasks(
            echo_data=echo_data,
            predict_data=predict_data,
            flash_data=flash_data,
            flash_sector=flash_sector,
            chunk_size=chunk_size,
        )

    def _register_tasks(
        self,
        *,
        echo_data: bytes,
        predict_data: bytes,
        flash_data: bytes,
        flash_sector: int,
        chunk_size: int,
    ) -> None:
        self.register_task(
            "fpga_power_on",
            task=lambda config: FPGA_powerOnTask(
                task_def_id=FPGA_POWER_ON_TASK_ID,
                need_ack=config.need_ack,
                need_checksum=config.need_checksum,
            ),
            benchmark_task=lambda config: BenchmarkFPGA_powerOnTask(
                task_def_id=BENCHMARK_FPGA_POWER_ON_TASK_ID,
                need_ack=config.need_ack,
                need_checksum=config.need_checksum,
            ),
        )

        self.register_task(
            "echo",
            task=lambda config: EchoTask(
                task_def_id=ECHO_TASK_ID,
                data=echo_data,
                need_ack=config.need_ack,
                need_checksum=config.need_checksum,
            ),
            benchmark_task=lambda config: BenchmarkEchoTask(
                task_def_id=BENCHMARK_ECHO_TASK_ID,
                data=echo_data,
                need_ack=config.need_ack,
                need_checksum=config.need_checksum,
            ),
        )

        self.register_task(
            "predict",
            task=lambda config: PredictTask(
                task_def_id=PREDICT_TASK_ID,
                data=predict_data,
                need_ack=config.need_ack,
                need_checksum=config.need_checksum,
            ),
            benchmark_task=lambda config: BenchmarkPredictTask(
                task_def_id=BENCHMARK_PREDICT_TASK_ID,
                data=predict_data,
                need_ack=config.need_ack,
                need_checksum=config.need_checksum,
            ),
        )

        self.register_task(
            "write_to_flash",
            task=lambda config: WriteToFlashTask(
                task_def_id=WRITE_TO_FLASH_TASK_ID,
                sector=flash_sector,
                data=flash_data,
                chunk_size=chunk_size,
                need_ack=config.need_ack,
                need_checksum=config.need_checksum,
            ),
            benchmark_task=lambda config: BenchmarkWriteToFlashTask(
                task_def_id=BENCHMARK_WRITE_TO_FLASH_TASK_ID,
                sector=flash_sector,
                need_ack=config.need_ack,
                need_checksum=config.need_checksum,
            ),
        )

        self.register_task(
            "read_skeleton_id",
            task=lambda config: ReadSkeletonIdTask(
                task_def_id=READ_SKELETON_ID_TASK_ID,
                need_ack=config.need_ack,
                need_checksum=config.need_checksum,
            ),
            benchmark_task=lambda config: BenchmarkReadSkeletonIdTask(
                task_def_id=BENCHMARK_READ_SKELETON_ID_TASK_ID,
                need_ack=config.need_ack,
                need_checksum=config.need_checksum,
            ),
        )

    def register_task(
        self,
        name: str,
        *,
        task: TaskFactory,
        benchmark_task: TaskFactory,
    ) -> None:
        if name in self._tasks:
            raise ValueError(f"Task '{name}' is already registered")

        self._tasks[name] = TaskDefinition(
            task=task,
            benchmark_task=benchmark_task,
        )

    def create_task(
        self,
        name: str,
        config: CommunicationConfig,
    ) -> Task:
        try:
            definition = self._tasks[name]
        except KeyError:
            raise ValueError(f"Unknown task '{name}'") from None

        return definition.task(config)

    def create_benchmark_task(
        self,
        name: str,
        config: CommunicationConfig,
    ) -> Task:
        try:
            definition = self._tasks[name]
        except KeyError:
            raise ValueError(f"Unknown task '{name}'") from None

        return definition.benchmark_task(config)

    @property
    def task_names(self) -> tuple[str, ...]:
        return tuple(self._tasks)

    def measure_task(
        self,
        name: str,
        iteration: int,
        config: CommunicationConfig,
    ) -> TaskMeasurement:
        benchmark_task = self.create_benchmark_task(
            name,
            config,
        )

        self._run_task(benchmark_task)

        core_time_us = benchmark_task.core_time_us

        task = self.create_task(
            name,
            config,
        )

        start = perf_counter_ns()

        self._run_task(task)

        remote_time_ns = perf_counter_ns() - start

        return TaskMeasurement(
            task=name,
            configuration=config.name,
            need_ack=config.need_ack,
            need_checksum=config.need_checksum,
            iteration=iteration,
            remote_time_ns=remote_time_ns,
            core_time_us=core_time_us,
        )


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="session", autouse=True)
def clean_benchmark_output() -> None:
    output_path.unlink(missing_ok=True)


@pytest.fixture(scope="session")
def fpga_remote_control(
    flashed_pico,
    wait_for_device,
):
    device = wait_for_device
    flash_data = BYTE_STREAM_PATH.read_bytes()

    with device.connect_sync() as stream:
        with FPGARemoteControl(
            stream,
            echo_data=bytes(256),
            predict_data=PREDICT_DATA,
            flash_data=flash_data,
            flash_sector=0,
            chunk_size=CHUNK_SIZE,
        ) as control:
            yield control


# ============================================================================
# Tests
# ============================================================================


class TestRemoteTaskBenchmark:
    ITERATIONS = 50

    TASKS = (
        "fpga_power_on",
        "echo",
        "predict",
        "write_to_flash",
        "read_skeleton_id",
    )

    @pytest.mark.parametrize("task_name", TASKS)
    @pytest.mark.parametrize(
        "config",
        COMMUNICATION_CONFIGS,
        ids=lambda config: config.name,
    )
    def test_remote_task_benchmark(
        self,
        fpga_remote_control: FPGARemoteControl,
        task_name: str,
        config: CommunicationConfig,
    ) -> None:
        for iteration in range(self.ITERATIONS):
            measurement = fpga_remote_control.measure_task(
                name=task_name,
                iteration=iteration,
                config=config,
            )

            pd.DataFrame(
                [
                    {
                        "task": measurement.task,
                        "configuration": measurement.configuration,
                        "need_ack": measurement.need_ack,
                        "need_checksum": measurement.need_checksum,
                        "iteration": measurement.iteration,
                        "remote_time_ns": measurement.remote_time_ns,
                        "remote_time_us": measurement.remote_time_us,
                        "core_time_us": measurement.core_time_us,
                        "overhead_us": measurement.overhead_us,
                    }
                ]
            ).to_csv(
                output_path,
                mode="a",
                header=not output_path.exists(),
                index=False,
            )
