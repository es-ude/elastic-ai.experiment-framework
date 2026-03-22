from enum import Enum


class CallType(Enum):
    IMMEDIATE = 0
    SCHEDULED = 1
    LOOP = 2
    OPEN_STREAM = 4
    RUN_SCHEDULED = 8
    FEATURES = 16  # query for supported feature set
