from dataclasses import dataclass


@dataclass
class NoAction:
    pass


@dataclass
class SendChunk:
    data: bytes
    need_ack: bool = False


@dataclass
class CloseTask:
    need_ack: bool = False


CallbackAction = SendChunk | NoAction | CloseTask
