from dataclasses import dataclass


@dataclass
class SendChunk:
    data: bytes
    need_ack: bool = False


@dataclass
class CloseTask:
    need_ack: bool = False


CallbackAction = SendChunk | CloseTask
