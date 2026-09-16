import asyncio

from ..remote_control.io_stream import IOStream
from .fpga_remote_control import FPGARemoteControl


class SyncFPGARemoteControl:
    def __init__(
        self,
        device: IOStream,
    ):
        self._async_control = FPGARemoteControl(device)
        self._loop =  asyncio.get_event_loop()
        self._loop.run_until_complete(self._async_control.__aenter__())

    def fpga_power_on(self):
        self._loop.run_until_complete(self._async_control.fpga_power_on())

    def fpga_power_off(self):
        self._loop.run_until_complete(self._async_control.fpga_power_off())

    def read_skeleton_id(self) -> str:
        return self._loop.run_until_complete(self._async_control.read_skeleton_id())

    def predict(self, data: bytes, result_size: int) -> bytes:
        return self._loop.run_until_complete(
            self._async_control.predict(data, result_size)
        )

    def upload_bitstream(self, flash_sector: int, path_to_bitstream: str):
        self._loop.run_until_complete(
            self._async_control.upload_bitstream(flash_sector, path_to_bitstream)
        )

    def _close(self) -> None:
        self._loop.run_until_complete(self._async_control.__aexit__(None, None, None))


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self._close()
