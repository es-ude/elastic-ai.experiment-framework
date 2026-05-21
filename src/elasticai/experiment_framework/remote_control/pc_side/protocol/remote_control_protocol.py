import logging
from typing import List, Optional

from ..network_layer import Connection
from .constants import MAX_CONNECTED_DEVICES, TransportType
from .device_session import DeviceSession

_logger = logging.getLogger(__name__)


class RemoteControlProtocol:
    """Device registry — connect, disconnect, find sessions."""

    def __init__(self, max_devices: int = MAX_CONNECTED_DEVICES) -> None:
        self._sessions: List[DeviceSession] = []
        self._max_devices = max_devices
        self._next_id = 0

    async def connect_tcp(self, host: str, port: int) -> DeviceSession:
        self._check_capacity()

        device_info = {"host": host, "port": str(port)}
        self._check_not_duplicate(device_info)

        con = Connection(transportType=TransportType.TCP, host=host, port=port)

        try:
            await con.connect()
            session = DeviceSession(self._next_id, device_info, con)
        except Exception as e:
            await con.close()
            raise e

        self._sessions.append(session)
        self._next_id += 1

        await session.start()

        _logger.debug("[CLIENT] device connected: %s", device_info)
        return session

    async def disconnect(self, session: DeviceSession) -> None:
        await session.stop()
        self._sessions.remove(session)
        _logger.debug("[CLIENT] device disconnected: %s", session.device_info)

    def find_by_info(self, device_info: dict) -> DeviceSession:
        result = [s for s in self._sessions if s.device_info == device_info]
        if not result:
            raise Exception(f"device not found: {device_info}")
        return result[0]

    def find_by_id(self, session_id: int) -> Optional[DeviceSession]:
        return next((s for s in self._sessions if s.id == session_id), None)

    def _check_capacity(self) -> None:
        if len(self._sessions) >= self._max_devices:
            raise RuntimeError("max devices reached")

    def _check_not_duplicate(self, device_info: dict) -> None:
        if any(s.device_info == device_info for s in self._sessions):
            raise Exception(f"device already connected: {device_info}")
