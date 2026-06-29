from contextlib import _AsyncGeneratorContextManager, asynccontextmanager
from dataclasses import dataclass
from typing import Protocol

from serial.tools import list_ports

from .connection_provider import ConnectionProvider
from .io_stream import IOStream


@dataclass(frozen=True)
class _DeviceSpec:
    pid: int
    vid: int
    name: str


class Device(Protocol):
    @property
    def name(self) -> str: ...

    def connect(self) -> _AsyncGeneratorContextManager[IOStream, None]: ...


class _SerialDevice(Device):
    def __init__(self, spec, port: str, baudrate: int = 115200):
        self._spec = spec
        self._port = port
        self._baudrate = baudrate

    @property
    def name(self) -> str:
        return self._spec.name

    @asynccontextmanager
    async def connect(self):
        provider = ConnectionProvider()
        async with provider.connectSerial(
            port=self._port,
            baudrate=self._baudrate,
        ) as stream:
            yield stream


def probe_for_devices(specs: set[_DeviceSpec]) -> list[Device]:
    discovered: list[Device] = []

    for spec in specs:
        try:
            port = detect_device(spec.pid, spec.vid)

            discovered.append(
                _SerialDevice(
                    spec=spec,
                    port=port,
                )
            )
        except RuntimeError:
            continue

    return discovered


def detect_device(pid: int, vid: int) -> str:
    all_ports = list_ports.comports()
    for port in all_ports:
        if getattr(port, "pid", None) == pid and getattr(port, "vid", None) == vid:
            return port.device
    else:
        raise RuntimeError(
            f"Failed to detect device {pid=}, {vid=}. Make sure it is "
            "connected. If this still fails you have to specify it manually."
        )
