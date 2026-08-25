import logging
from pathlib import Path

import pytest
import time

from elasticai.experiment_framework.env5.sync_fpga_remote_control import (
    SyncFPGARemoteControl,
)

logging.basicConfig(format="%(message)s")
logger = logging.getLogger(__name__)

BYTE_STREAM_PATH = Path("tests/fpga/env5_top_reconfig.bin")

@pytest.fixture(scope="session")
def fpga_remote_control(flashed_pico, wait_for_device):
    device = wait_for_device

    with device.connect_sync() as stream:
        with SyncFPGARemoteControl(stream) as control:
            yield control


def test_fpga_flashing(fpga_remote_control):
    fpga_remote_control.fpga_power_off()
    fpga_remote_control.upload_bitstream(
       flash_sector=0,
        path_to_bitstream=BYTE_STREAM_PATH,
        timer=False,
        need_ack=True
    )
    fpga_remote_control.fpga_power_on()
    fpga_remote_control.read_skeleton_id()
    fpga_remote_control.predict(b"\x01",1)

def test_fpga_flashing_timer(fpga_remote_control):
    fpga_remote_control.fpga_power_off()
    fpga_remote_control.upload_bitstream(
       flash_sector=0,
        path_to_bitstream=BYTE_STREAM_PATH,
        timer=True
    )
    fpga_remote_control.fpga_power_on()
    fpga_remote_control.read_skeleton_id()
    fpga_remote_control.predict(b"\x01",1)

def test_fpga_flashing_timer_ack(fpga_remote_control):
    fpga_remote_control.fpga_power_off()
    fpga_remote_control.upload_bitstream(
       flash_sector=0,
        path_to_bitstream=BYTE_STREAM_PATH,
        timer=True,
        need_ack=True
    )
    fpga_remote_control.fpga_power_on()
    fpga_remote_control.read_skeleton_id()
    fpga_remote_control.predict(b"\x01",1)

def test_fpga_flashing_timer_checksum(fpga_remote_control):
    fpga_remote_control.fpga_power_off()
    fpga_remote_control.upload_bitstream(
       flash_sector=0,
        path_to_bitstream=BYTE_STREAM_PATH,
        timer=True,
        need_checksum=True
    )
    fpga_remote_control.fpga_power_on()
    fpga_remote_control.read_skeleton_id()
    fpga_remote_control.predict(b"\x01",1)

def test_fpga_flashing_timer_ack_checksum(fpga_remote_control):
    fpga_remote_control.fpga_power_off()
    fpga_remote_control.upload_bitstream(
       flash_sector=0,
        path_to_bitstream=BYTE_STREAM_PATH,
        timer=True,
        need_checksum=True,
        need_ack=True
    )
    fpga_remote_control.fpga_power_on()
    fpga_remote_control.read_skeleton_id()
    fpga_remote_control.predict(b"\x01",1)