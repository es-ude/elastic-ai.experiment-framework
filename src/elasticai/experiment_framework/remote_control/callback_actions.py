from enum import Enum


class CallbackAction(Enum):
    SEND_CHUNK = "send_chunk"
    CLOSE_TASK = "close_task"
