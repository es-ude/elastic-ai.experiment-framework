import pytest

from elasticai.experiment_framework.remote_control.devices import (
    detect_device,
    probe_for_devices,
)


@pytest.mark.hardware
def test_detect_env5() -> None:
    """device has to be connected to pc for this test to pass."""
    assert len(detect_device(10, 11914))


@pytest.mark.hardware
def test_probe_for_device() -> None:
    devices = probe_for_devices()
    assert len(devices) > 0
    assert "env5" in [d.name for d in devices]
