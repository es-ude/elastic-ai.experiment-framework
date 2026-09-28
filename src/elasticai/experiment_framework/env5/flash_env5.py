import logging
import subprocess
import time
from pathlib import Path

import pytest

from elasticai.experiment_framework.remote_control.devices import (
    _DeviceSpec,
    probe_for_devices,
)

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

logger = logging.getLogger(__name__)


def build_pico_firmware():
    configure = subprocess.run(
        ["cmake", "--preset", "pico-debug"],
        cwd=SERVER_CMAKE,
        capture_output=True,
        text=True,
    )
    if configure.returncode != 0:
        pytest.fail(f"CMake configure (pico) failed:\n{configure.stderr}")
    logger.info("2 configure done")

    build = subprocess.run(
        ["cmake", "--build", "--preset", "pico-debug"],
        cwd=SERVER_CMAKE,
        capture_output=True,
        text=True,
    )
    if build.returncode != 0:
        pytest.fail(
            f"CMake build (pico) failed\n\nSTDOUT:\n{build.stdout}\n\n"
            f"STDERR:\n{build.stderr}"
        )
    logger.info("3 build done")

    if not PICO_UF2.exists():
        pytest.fail(f"Expected UF2 not found at {PICO_UF2}")

    logger.info("4 uf2 exists")


def flashed_pico():
    build_pico_firmware()
    print("Flashing Pico with picotool")

    flash = subprocess.run(
        ["picotool", "load", str(PICO_UF2), "-f", "--execute"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    logger.error(f"picotool return code: {flash.returncode}")
    logger.error(f"picotool stdout:\n{flash.stdout}")
    logger.error(f"picotool stderr:\n{flash.stderr}")

    if flash.returncode != 0:
        pytest.fail("picotool failed")

    if "Tracking device serial number  for reboot" in flash.stdout:
        pytest.fail(
            "picotool could not detect Pico serial number. "
            "USB reconnect via usbipd/WSL probably failed."
        )

    logger.info("Pico flashed successfully")


def wait_for_device(timeout=15):
    start = time.time()

    logger.info("waiting for device")

    while time.time() - start < timeout:
        devices = probe_for_devices(SPECS)
        if devices:
            time.sleep(0.5)
            return devices[0]
        time.sleep(0.5)
    logger.info("waiting for device 2")

    raise RuntimeError("Pico did not re-enumerate")
