from enum import Enum, auto


class Verbosity(Enum):
    ONLY_ERRORS = auto()
    OUT_AND_ERRORS = auto()
    ALL = auto()
