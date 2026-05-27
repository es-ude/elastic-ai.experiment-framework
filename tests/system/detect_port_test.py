from elasticai.experiment_framework.remote_control.devices import (
    detect_device,
    probe_for_devices,
)
from elasticai.experiment_framework.remote_control.message import Message


def test_detect_env5() -> None:
    """device has to be connected to pc for this test to pass."""
    assert len(detect_device(10, 11914))


def test_probe_for_device() -> None:
    devices = probe_for_devices()
    assert len(devices) > 0
    assert "env5" in [d.name for d in devices]


def test_talk_to_device() -> None:
    device = probe_for_devices()[0]
    with device.connect() as iostream:
        iostream.write(Message(8, bytes.fromhex("00")).to_bytes())
        result = iostream.read(6)
    assert result.hex(" ") == "01 00 00 00 00 01"
