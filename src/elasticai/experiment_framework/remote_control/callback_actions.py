from dataclasses import dataclass


@dataclass
class NoAction: ...


@dataclass
class SendChunk:
    data: bytes


CallbackAction = SendChunk | NoAction
