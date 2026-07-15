import logging
import subprocess
import time
from pathlib import Path

import pytest

from elasticai.experiment_framework.remote_control.devices import (
    _DeviceSpec,
    probe_for_devices,
)

logging.basicConfig(format="%(message)s")
_logger = logging.getLogger(__name__)

SERIAL_PORT = "/dev/tty/ACM0"
SERIAL_BAUDRATE = 115200

SPECS: set[_DeviceSpec] = {
    _DeviceSpec(10, 11914, "env5"),
}
PICO_USB_ID_BOOTMODE = "2e8a:0003"
PICO_USB_ID_RUNNINGMODE = "2e8a:000a"

SERVER_CMAKE = "example-firmwares/remote_control"
PICO_BUILD_DIR = Path(SERVER_CMAKE) / "build" / "pico-debug" / "src" / "app"
PICO_UF2 = PICO_BUILD_DIR / "remote_control.uf2"


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
    print("2 configure done", flush=True)

    build = subprocess.run(
        ["cmake", "--build", "--preset", "pico-debug"],
        cwd=SERVER_CMAKE,
        # capture_output=True,
        # text=True,
    )
    if build.returncode != 0:
        pytest.fail(
            f"CMake build (pico) failed\n\nSTDOUT:\n{build.stdout}\n\n"
            f"STDERR:\n{build.stderr}"
        )
    print("3 build done", flush=True)

    if not PICO_UF2.exists():
        pytest.fail(f"Expected UF2 not found at {PICO_UF2}")

    print("4 uf2 exists", flush=True)





@pytest.fixture(scope="session")
def flashed_pico(build_pico_firmware):
    print("Flashing Pico with picotool", flush=True)

    flash = subprocess.run(
        ["picotool", "load", str(PICO_UF2), "-f", "--execute"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    print(flash.stdout, end="", flush=True)

    if flash.returncode != 0:
        pytest.fail("picotool failed")

    if "Tracking device serial number  for reboot" in flash.stdout:
        pytest.fail(
            "picotool could not detect Pico serial number. "
            "USB reconnect via usbipd/WSL probably failed."
        )

    print("Pico flashed successfully", flush=True)


@pytest.fixture(scope="session")
def wait_for_device(timeout=15):
    start = time.time()

    print("waiting for device")

    while time.time() - start < timeout:
        devices = probe_for_devices(SPECS)
        if devices:
            time.sleep(0.5)
            return devices[0]
        time.sleep(0.5)
    print("waiting for device 2")

    raise RuntimeError("Pico did not re-enumerate")