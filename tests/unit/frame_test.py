from elasticai.experiment_framework.remote_control.frame import FrameWriter


def test_frame_writer():
    frame = bytes([1, 0, 0xAA])
    buffer = bytearray()
    writer = FrameWriter(buffer)
    i = 0
    while not writer.has_finished():
        writer.write(frame[i : i + 1])
    assert bytes(buffer) == frame
