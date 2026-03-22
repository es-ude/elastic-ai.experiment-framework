import contextlib
from collections.abc import Generator
import logging
import sys
from pathlib import Path

from serial import Serial

from .io_stream import IOStream
from .remote_control_protocol import RemoteControlProtocol
from .devices import Device, probe_for_devices
import click


@contextlib.contextmanager
def connect_remote_control(device: Device) -> Generator["RemoteControl"]:
    with device.connect() as connected:
        yield RemoteControl(connected)


class RemoteControl:
    def __init__(self, device: IOStream):
        self._rcp = RemoteControlProtocol(device)
        self._rcp.request_flash_chunk_size()

    def deploy_model(self, flash_sector: int, path_to_bitstream_dir: str):
        Path(path_to_bitstream_dir)
        # with open(directory / "meta.json", "r") as f:
        #     meta = json.load(f)
        # skeleton_id = bytes.fromhex(meta["skeleton_id"])
        self._rcp.deploy_model(
            flash_sector, bytes.fromhex("00000000000000000000000000000000")
        )
        print(self._rcp.read_skeleton_id())

    def upload_bitstream(self, flash_sector: int, path_to_bitstream: str):
        directory = Path(path_to_bitstream)
        with open(directory, "r+b") as f:
            config = f.read()
        self._rcp.write_to_flash(sector=flash_sector, data=config)

    def read_from_flash(self, flash_sector: int, num_bytes: int) -> bytes:
        raise NotImplementedError

    def predict(self, data: bytes, result_size: int) -> bytes:
        return self._rcp.predict(data, result_size)

    def read_skeleton_id(self) -> str:
        return self._rcp.read_skeleton_id().hex(sep=" ")

    def fpga_power_on(self) -> None:
        self._rcp.fpga_power_on()

    def fpga_power_off(self) -> None:
        self._rcp.fpga_power_off()

    def fpga_leds(self, leds: tuple[bool, bool, bool]):
        self._rcp.set_fpga_leds(leds)

    def mcu_leds(self, leds: tuple[bool, bool, bool]):
        self._rcp.set_mcu_leds(leds)

    def send_command(self, cmd_id: int, data: str | bytes, result_size: int):
        return self._rcp.send_custom_command(
            cmd_id,
            payload=bytes.fromhex(data) if isinstance(data, str) else data,
            response_size=result_size,
        )


@click.group()
@click.option(
    "-p",
    "--port",
    type=str,
    help="serial port, the default is auto, which will probe for supported devices and pick the first available one",
    default="auto",
)
@click.option("-v", "--verbose", is_flag=True)
@click.pass_context
def main(ctx, port, verbose):
    """Interact with an MCU and the FPGA connected to it."""
    if verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            force=True,
            format="{levelname}:: {pathname}:{lineno}\n\t{message}",
            style="{",
        )
    if port == "auto":
        devices = probe_for_devices()
        if len(devices) == 0:
            raise RuntimeError("failed to autodetect devices, specify port manually.")
        device = devices[0]
        ctx.obj = ctx.with_resource(device.connect())
    else:
        ctx.obj = ctx.with_resource(Serial(port))


@main.command
@click.option(
    "-fa", "--flash-address", type=int, help="destination address in flash", default=0
)
@click.argument("binfile")
@click.pass_obj
def upload(obj, flash_address, binfile):
    """Upload a binfile to the specified flash sector address"""
    rc = RemoteControl(obj)
    rc.upload_bitstream(flash_address, binfile)


@main.command
@click.pass_obj
def get_id(obj):
    rc = RemoteControl(obj)
    rc.read_skeleton_id()


@main.command
@click.pass_obj
@click.option("-rs", "--result-size", type=int)
@click.argument("data")
def predict(obj, result_size, data):
    if data == "--":
        data = sys.stdin.buffer.read()
    else:
        data = bytes.fromhex(data)
    rc = RemoteControl(obj)
    result = rc.predict(data, result_size)
    print(result.hex(" "))


@main.command
@click.pass_obj
@click.option("-fa", "--flash-address")
def load_bitstream(obj, address):
    """Load the bitstream/design/configuration from the specified flash address to the fpga."""
    rc = RemoteControl(obj)
    rc.deploy_model(address, "")


@main.command
@click.pass_obj
@click.argument("led_state", type=str)
def mcu_leds(obj, led_state):
    """Specify the led state as a three digit bit vector."""
    rc = RemoteControl(obj)
    rc.mcu_leds(tuple(led == "1" for led in led_state))


@main.group
def fpga():
    pass


@fpga.command("on")
@click.pass_obj
def fpga_on(obj):
    """Turn fpga on."""
    rc = RemoteControl(obj)
    rc.fpga_power_on()


@fpga.command("off")
@click.pass_obj
def fpga_off(obj):
    """Turn fpga off."""
    rc = RemoteControl(obj)
    rc.fpga_power_off()
