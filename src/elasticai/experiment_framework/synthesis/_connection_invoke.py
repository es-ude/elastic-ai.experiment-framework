from pathlib import Path
from contextlib import AbstractContextManager
from .verbosity import Verbosity
import shutil
from ._connection import Connection


class ConnectionWrapperForInvoke(Connection):
    def __init__(self, wrapped, verbosity: Verbosity):
        self._wrapped = wrapped
        self._verbosity = verbosity

    def run(self, cmd: str):
        match self._verbosity:
            case Verbosity.ONLY_ERRORS:
                return self._wrapped.run(cmd, hide="out")
            case Verbosity.ALL:
                return self._wrapped.run(cmd, echo=True)
            case _:
                return self._wrapped.run(cmd)

    def cd(self, path: str | Path) -> AbstractContextManager:
        return self._wrapped.cd(path)

    def get(self, src: str, dst: str | Path):
        shutil.copy(src, dst)

    def put(self, src: str | Path, dst: str):
        shutil.copy(src, dst)

    def __getattr__(self, name):
        return getattr(self._wrapped, name)
