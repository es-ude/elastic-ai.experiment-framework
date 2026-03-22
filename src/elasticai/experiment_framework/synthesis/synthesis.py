import logging
import warnings
from collections.abc import Mapping, Iterator, Iterable
import os
import dataclasses
from abc import abstractmethod
from dataclasses import dataclass
from enum import StrEnum, auto
from pathlib import Path
from typing import Protocol, Self, runtime_checkable, override
from hashlib import blake2s


class TargetPlatforms(StrEnum):
    env5 = auto()


@dataclass(frozen=True)
class SynthesisConfig:
    host: str = "localhost"
    ssh_user: str = ""
    ssh_port: int = 22
    target: str = TargetPlatforms.env5
    working_dir: str = "~/"
    key: str = "synthesis"
    quiet: bool = True


@runtime_checkable
class SynthesisStrategy[S: SynthesisConfig](Protocol):
    @abstractmethod
    def get_config(self) -> S:
        """Returns the concrete SynthesisConfig object used for this strategy."""
        ...

    @abstractmethod
    def set_config(self, config: SynthesisConfig) -> Self:
        """Will try to infer missing fields from environment variables using `load_synthesis_config_from_env`."""
        ...

    @abstractmethod
    def synthesize(
        self, src_dir: Path | str, out_path: Path | str | None = None
    ) -> Path:
        """run synthesis with files in src_dir and save the results in out_path, returns the resulting out_path.

        If out_path is not specified, the result is stored in a sibling
        folder of src_dir, called `synthesis_result.tar.gz`.

        If out_path is ends with .tar.gz or .zip it will be stored in the
        corresponding archive if supported or raise an error otherwise.
        """
        ...


class CachedSynthesis[S: SynthesisConfig](SynthesisStrategy):
    def __init__(self, wrapped: SynthesisStrategy[S]) -> None:
        self._wrapped = wrapped
        self._includes: tuple[str, ...] = ("**/*.vhd", "**/*.v", "**/*.xdc")
        self._excludes: tuple[str, ...] = tuple()
        self._logger = logging.getLogger(__name__)

    @override
    def set_config(self, config: SynthesisConfig) -> Self:
        self._wrapped.set_config(config)
        return self

    @override
    def get_config(self) -> Self:
        self._wrapped.get_config()
        return self

    def include(self, globs: Iterable[str]) -> None:
        self._includes = tuple(globs)

    def exclude(self, globs: Iterable[str]) -> None:
        self._excludes = tuple(globs)

    @override
    def synthesize(
        self,
        src_dir: Path | str,
        out_path: Path | str | None = None,
        cache_dir: str | Path = "$XDG_CACHE_HOME/eaixp/synthesis/",
    ) -> Path:
        """Cache synthesis results and create a symlink to the cache hit at `out_path`."""
        src_dir = Path(src_dir)
        digest = self._compute_hash(src_dir)
        cache_dir = self._normalize_cache_dir(cache_dir)
        cache_dir.mkdir(exist_ok=True)
        digest_dir = cache_dir / ("/".join([digest[0:3], digest[3:]]) + "/")
        digest_dir.parent.mkdir(exist_ok=True)

        if not digest_dir.exists() or len(list(digest_dir.iterdir())) == 0:
            self._logger.info("cache miss -> run synthesis...")
            target = digest_dir
            if str(out_path).endswith(".tar.gz"):
                target = digest_dir / "synthesis_result.tar.gz"

            self._wrapped.synthesize(src_dir, target)

        return self._create_symlink(digest_dir, out_path)

    def _path_matches(self, path: Path, patterns: Iterable[str]) -> bool:
        return any((path.match(pattern) for pattern in patterns))

    def _is_included(self, path: Path) -> bool:
        return self._path_matches(path, self._includes)

    def _is_excluded(self, path: Path) -> bool:
        return self._path_matches(path, self._excludes)

    def _get_files_for_hashing(self, src_dir: Path) -> Iterator[Path]:
        def file_paths() -> Iterator[Path]:
            for dirpath, dirnames, filenames in src_dir.walk():
                for filename in filenames:
                    yield dirpath / filename

        for path in file_paths():
            if self._is_included(path) and not self._is_excluded(path):
                yield path

    def _compute_hash(self, src_dir: Path) -> str:
        hashobj = blake2s()
        for f in self._get_files_for_hashing(src_dir):
            with f.open("b+r") as opened:
                hashobj.update(opened.read())
        return hashobj.hexdigest()

    def _normalize_cache_dir(self, cache_dir: str | Path) -> Path:
        if isinstance(cache_dir, str):
            cache_dir = os.path.expandvars(cache_dir)
            if "$XDG_CACHE_HOME" in cache_dir:
                warnings.warn("XDG_CACHE_HOME not set, using default ~/.cache/")
                cache_dir = "~/.cache/eaixp"
            return Path(os.path.expanduser(cache_dir))

        return cache_dir

    def _create_symlink(self, digest_dir: Path, out_path: Path | str | None) -> Path:
        if out_path is None:
            return digest_dir
        else:
            out_path = Path(out_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            if out_path.is_dir():
                out_path.symlink_to(digest_dir, target_is_directory=True)
            else:
                out_path.symlink_to(target=digest_dir / out_path.name)
            return out_path


def load_synthesis_config_from_env[T: SynthesisConfig](
    t: type[T], env: Mapping[str, str] | None = None
) -> T:
    """Create a SynthesisConfig from a mapping or current environment variables.

    Instead of specifying `env` explicitly just use the concrete type to construct your object.

    Example for environemnt variables

    ```
    SYNTH_HOST = "192.168.1.34"
    SYNTH_SSH_USER = "elasticai"
    SYNTH_TARGET = "env5"
    SYNTH_WORKING_DIR = "/home/ies/synthesis"
    SYNTH_KEY = "hw_testing"
    ```
    """
    if env is None:
        env = os.environ
    default = dataclasses.asdict(t())

    fields = {field.name: field for field in dataclasses.fields(t)}

    def _bool(value: str) -> bool:
        return value in ("True", True)

    def get(key: str) -> str | int | bool:
        value = env.get(f"SYNTH_{key.upper()}", default.get(key, ""))
        _type = fields[key].type
        _type_map = {
            "str": str,
            "int": int,
            "bool": _bool,
        }
        if isinstance(_type, type):
            _type_str = _type.__name__.removeprefix("<class '").removesuffix("'>")
        else:
            _type_str = _type
        if _type_str in _type_map:
            return _type_map[_type_str](value)

        raise TypeError(f"unsupported synthesis config type {_type_str}")

    loaded = {key: get(key) for key in fields}

    return t(**loaded)  # type: ignore
