from dataclasses import dataclass


@dataclass
class NoAction:
    pass


@dataclass
class SendChunk:
    data: bytes
    need_ack: bool | None = None


@dataclass
class CloseTask:
    need_ack: bool | None = None


CallbackAction = SendChunk | NoAction | CloseTask
