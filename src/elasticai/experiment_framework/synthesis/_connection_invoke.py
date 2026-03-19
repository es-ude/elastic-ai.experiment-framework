from pathlib import Path
from contextlib import AbstractContextManager
from .verbosity import Verbosity
import shutil
from ._connection import Connection
from invoke.context import Context


class ConnectionWrapperForInvoke(Connection):
    def __init__(self, wrapped: Context, verbosity: Verbosity):
        self._wrapped = wrapped
        self._verbosity = verbosity

    def run(self, cmd: str) -> None:
        match self._verbosity:
            case Verbosity.ONLY_ERRORS:
                self._wrapped.run(cmd, hide="out", in_stream=False)
            case Verbosity.ALL:
                self._wrapped.run(cmd, echo=True, in_stream=False)
            case _:
                self._wrapped.run(cmd, in_stream=False)

    def cd(self, path: str | Path) -> AbstractContextManager:
        return self._wrapped.cd(path)

    def get(self, src: str, dst: str | Path):
        shutil.copy(src, dst)

    def put(self, src: str | Path, dst: str):
        shutil.copy(src, dst)

    def __getattr__(self, name):
        return getattr(self._wrapped, name)
