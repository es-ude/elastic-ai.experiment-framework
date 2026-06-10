from dataclasses import dataclass


@dataclass
class SendChunk:
    data: bytes
    need: bool = False

@dataclass
class CloseTask:
    need: bool = False

CallbackAction = SendChunk | CloseTask
