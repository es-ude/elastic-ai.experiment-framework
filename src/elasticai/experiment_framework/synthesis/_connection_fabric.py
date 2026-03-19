from pathlib import Path
from contextlib import AbstractContextManager
from fabric import Connection as _fabConnection
from .verbosity import Verbosity
from ._connection import Connection


class ConnectionWrapperForFabric(Connection):
    def __init__(self, wrapped: _fabConnection, verbosity: Verbosity):
        self._wrapped = wrapped
        self._verbosity = verbosity

    def cd(self, path: str | Path) -> AbstractContextManager:
        return self._wrapped.cd(path)

    def get(self, src: str, dst: str | Path) -> None:
        self._wrapped.get(src, dst)

    def put(self, src: str | Path, dst: str) -> None:
        self._wrapped.put(src, dst)

    def run(self, cmd: str):
        match self._verbosity:
            case Verbosity.ONLY_ERRORS:
                return self._wrapped.run(cmd, hide="out", in_stream=False)
            case Verbosity.ALL:
                return self._wrapped.run(cmd, echo=True, in_stream=False)
            case _:
                return self._wrapped.run(cmd, in_stream=False)
