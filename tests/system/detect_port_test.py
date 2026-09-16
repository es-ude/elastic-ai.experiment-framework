from elasticai.experiment_framework.remote_control.devices import (
    _DeviceSpec,
    detect_device,
    probe_for_devices,
)

SPECS: set[_DeviceSpec] = {
    _DeviceSpec(10, 11914, "env5"),
}


def test_detect_env5() -> None:
    """device has to be connected to pc for this test to pass."""
    assert len(detect_device(10, 11914))


def test_probe_for_device() -> None:
    devices = probe_for_devices(SPECS)
    assert len(devices) > 0
    assert "env5" in [d.name for d in devices]
