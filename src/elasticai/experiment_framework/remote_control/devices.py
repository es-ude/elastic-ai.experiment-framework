from collections.abc import Generator
from contextlib import contextmanager
from abc import abstractmethod
from typing import Protocol, cast
from serial.tools import list_ports
from dataclasses import dataclass
from serial import Serial as _Serial
from .io_stream import IOStream


@dataclass(frozen=True)
class _DeviceSpec:
    pid: int
    vid: int
    name: str


_SPECS = {_DeviceSpec(10, 11914, "env5")}


class Device(Protocol):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @contextmanager
    @abstractmethod
    def connect(self) -> Generator[IOStream]: ...


class _SerialDevice(Device):
    def __init__(self, spec: _DeviceSpec, comport: str) -> None:
        self._spec = spec
        self._comport = comport

    @property
    def name(self) -> str:
        return self._spec.name

    @contextmanager
    def connect(self) -> Generator[IOStream]:
        with _Serial(self._comport) as opened:
            yield _SerialIOStream(opened)


class _SerialIOStream(IOStream):
    def __init__(self, _serial: _Serial):
        self._serial = _serial

    def write(self, data: bytes | bytearray, /) -> int:
        return cast(int, self._serial.write(data))

    def read(self, num_bytes: int, /) -> bytes:
        return self._serial.read(num_bytes)


def probe_for_devices() -> list[Device]:
    discovered: list[Device] = []
    for spec in _SPECS:
        try:
            comport = detect_device(spec.pid, spec.vid)
            discovered.append(_SerialDevice(spec, comport=comport))
        except RuntimeError:
            continue
    return discovered


def detect_device(pid: int, vid: int) -> str:
    all_ports = list_ports.comports()
    for port in all_ports:
        if (port.pid, port.vid) == (pid, vid):
            return port.device
    else:
        raise RuntimeError(
            f"Failed to detect device {pid=}, {vid=}. Make sure it is connected. If this still fails you have to specify it manually."
        )
