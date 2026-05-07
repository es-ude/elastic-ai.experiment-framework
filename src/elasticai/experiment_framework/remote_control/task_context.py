import asyncio
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class TaskContext:
    transaction_id: int

    state: str = "opening"
    next_data_id: int = 0
    received_data: bytearray = field(default_factory=bytearray)

    opened_event: asyncio.Event = field(default_factory=asyncio.Event)
    finished_event: asyncio.Event = field(default_factory=asyncio.Event)

    _pending_acks: Dict[int, asyncio.Future] = field(default_factory=dict)

    @property
    def is_open(self) -> bool:
        return self.state == "opened"

    @property
    def is_finished(self) -> bool:
        return self.state == "finished"
