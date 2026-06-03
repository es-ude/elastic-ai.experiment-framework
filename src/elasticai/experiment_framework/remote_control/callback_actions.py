from dataclasses import dataclass


@dataclass
class SendChunk:
    data: bytes


CallbackAction = SendChunk
