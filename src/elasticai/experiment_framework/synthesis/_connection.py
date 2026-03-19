from abc import abstractmethod
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Protocol


class Connection(Protocol):
    @abstractmethod
    def run(self, cmd: str) -> None: ...
    @abstractmethod
    def cd(self, path: str | Path) -> AbstractContextManager: ...
    @abstractmethod
    def get(self, src: str, dst: str | Path) -> None: ...
    @abstractmethod
    def put(self, src: str | Path, dst: str) -> None: ...
