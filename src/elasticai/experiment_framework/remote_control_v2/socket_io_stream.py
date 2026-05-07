from contextlib import contextmanager
from collections.abc import Generator
from .io_stream import IOStream
import socket


class SocketIOStream:
    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def write(self, data: bytes | bytearray, /) -> int:
        return self._sock.send(data)

    def read(self, num_bytes: int, /) -> bytes:
        buf = bytearray()
        while len(buf) < num_bytes:
            chunk = self._sock.recv(num_bytes - len(buf))
            if not chunk:
                raise ConnectionError("Connection closed")
            buf.extend(chunk)
        return bytes(buf)

    @contextmanager
    def connect(self) -> Generator[IOStream]:
        self._sock.connect((self._host, self._port))
        try:
            yield self
        finally:
            self._sock.close()