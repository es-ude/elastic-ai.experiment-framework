from contextlib import ExitStack
from typing import Self, override, cast
import dataclasses

from elasticai.experiment_framework.synthesis.synthesis import (
    CachedSynthesis,
    TargetPlatforms,
    SynthesisConfig as _SynthConfig,
    SynthesisStrategy as _SynthStrat,
    load_synthesis_config_from_env,
)
from .verbosity import Verbosity
from dataclasses import dataclass
import logging
from fabric import Connection as _fabConnection
import click
from pathlib import Path
from tempfile import TemporaryDirectory
from tarfile import open as tar_open
from string import Template
from invoke import Context as _invContext
import os
import shlex
from ._connection import Connection as _Connection
from ._connection_fabric import ConnectionWrapperForFabric as _fabConnectionWrapper
from ._connection_invoke import ConnectionWrapperForInvoke as _invokeConnection


_fpga_model_for_platform = {TargetPlatforms.env5: "xc7s15ftgb196-2"}

_SRCS_FILE_BASE_NAME = "synth_srcs"
_SRCS_FILE_NAME = f"{_SRCS_FILE_BASE_NAME}.tar.gz"
_TCL_SCRIPT_NAME = "autobuild.tcl"

_SYNTH_HOST_ENVVARS = ("SYNTH_SERVER", "SYNTH_HOST")
_SYNTH_SSH_USER_ENVVARS = ("SYNTH_SSH_USER",)
_SYNTH_SSH_PORT_ENVVARS = ("SYNTH_SSH_PORT",)
_SYNTH_TARGET_ENVVARS = ("SYNTH_TARGET",)
_SYNTH_REMOTE_WORKING_DIR_ENVVARS = ("SYNTH_REMOTE_WORKING_DIR",)
_SYNTH_VIVADO_PATH_ENVVARS = ("SYNTH_VIVADO_PATH",)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _SynthesisConfig(_SynthConfig):
    vivado_path: str = "/tools/Xilinx/Vivado/2023.1/bin/vivado"


class CachedVivadoSynthesis(CachedSynthesis[_SynthesisConfig]):
    def __init__(self) -> None:
        super().__init__(VivadoSynthesis())

    def set_vivado_path(self, path: str) -> Self:
        cast(VivadoSynthesis, self._wrapped).set_vivado_path(path)
        return self


class VivadoSynthesis(_SynthStrat):
    def __init__(self) -> None:
        self._config: _SynthesisConfig | None = None

    def get_config(self) -> _SynthesisConfig:
        if self._config is None:
            self._config = load_synthesis_config_from_env(_SynthesisConfig)
        return self._config

    def set_vivado_path(self, path: str) -> Self:
        self._config = dataclasses.replace(self.get_config(), vivado_path=path)
        return self

    @override
    def set_config(self, config: _SynthConfig) -> Self:
        self._config = dataclasses.replace(
            self.get_config(), **dataclasses.asdict(config)
        )
        return self

    @override
    def synthesize(
        self, src_dir: Path | str, out_path: Path | str | None = None
    ) -> Path:
        config = self.get_config()
        old_style_config = _OldSynthConfig(
            config.host,
            config.ssh_user,
            config.ssh_port,
            config.target,
            f"{config.working_dir}/{config.key}/",
            config.vivado_path,
            config.quiet,
        )
        return _run_synthesis(Path(src_dir), old_style_config, out_path)


@dataclass
class _OldSynthConfig:
    host: str
    ssh_user: str
    ssh_port: int
    target: str
    remote_working_dir: str
    vivado_path: str
    quiet: bool


def _run_synthesis(
    src_dir: Path, config: _OldSynthConfig, out_path: Path | str | None = None
) -> Path:
    connection = _create_connection(
        config.host, config.ssh_user, config.ssh_port, config.quiet
    )

    logger.info("connecting to %s as %s", config.host, config.ssh_user)
    logger.info("uploading %s", src_dir.absolute())
    src_dir = src_dir.absolute()
    with ExitStack() as ctx_stack:
        if not out_path:
            out_path = src_dir.parent.absolute()
        else:
            out_path = Path(out_path)
        if out_path.is_dir():
            tmp_target_dir = TemporaryDirectory("synth_results")
            target_file = (
                Path(ctx_stack.enter_context(tmp_target_dir))
                / "vivado_run_results.tar.gz"
            )
        elif str(out_path).endswith(".tar.gz"):
            target_file = out_path
        else:
            raise ValueError(f"unsupported output path format {out_path}")
        project_name = "AI_Accel"

        if out_path.exists():
            logger.info(
                "skipping %s because target file %s already exists",
                src_dir,
                target_file.absolute(),
            )
            return out_path
        if "./" in config.remote_working_dir:
            raise ValueError("illegal remote working directory")
        with TemporaryDirectory(suffix="synth_server") as tmp_dir:
            logger.info("preparing files in %s", tmp_dir)
            tmp_dir = Path(tmp_dir)
            _write_tcl_script(
                tmp_dir,
                project_name=project_name,
                part_number=_fpga_model_for_platform[config.target],
                remote_working_dir=config.remote_working_dir,
                num_jobs=12,
            )
            logger.info("archiving srcs")
            srcs_archive = _create_srcs_archive(tmp_dir, src_dir)
            logger.info("uploading srcs to server")

            for name in [
                "*.log",
                "*.jou",
                "results",
                _SRCS_FILE_BASE_NAME,
            ]:
                try_remove_recursively(
                    connection, f"{config.remote_working_dir}/{name}"
                )
            connection.run(
                f"mkdir -p {config.remote_working_dir}/{_SRCS_FILE_BASE_NAME}"
            )
            connection.put(
                srcs_archive,
                f"{config.remote_working_dir}/{_SRCS_FILE_NAME}".removeprefix("~/"),
            )
        with connection.cd(config.remote_working_dir):
            logger.info("unpacking srcs on server")
            connection.run(
                "tar -C {dir} -xzf {srcs}".format(
                    dir=_SRCS_FILE_BASE_NAME, srcs=_SRCS_FILE_NAME
                )
            )
            logger.info("starting vivado implementation run")
            connection.run(
                "{vivado} -mode tcl -source {srcs}/{tcl_script}".format(
                    vivado=config.vivado_path,
                    srcs=_SRCS_FILE_BASE_NAME,
                    tcl_script=_TCL_SCRIPT_NAME,
                )
            )
            logger.info("vivado done")
            for cmd in [
                "mkdir -p results/synth",
                "mkdir results/impl",
                f"cp {project_name}.runs/impl_1/*.bin results/impl/",
                f"cp {project_name}.runs/impl_1/*.rpt results/impl/",
                f"cp {project_name}.runs/synth_1/*.rpt results/synth/",
                "tar -czf results.tar.gz results",
            ]:
                connection.run(cmd)
            connection.get(
                f"{config.remote_working_dir}/results.tar.gz",
                target_file,
            )
        if target_file != out_path:
            out_path.mkdir(exist_ok=True, parents=True)
            with tar_open(target_file, "r") as results:
                results.extractall(out_path)
        return out_path


@click.command()
@click.argument(
    "src_dir",
    type=click.Path(
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        writable=True,
        path_type=Path,
    ),
)
@click.option(
    "--host",
    envvar=_SYNTH_HOST_ENVVARS,
    default="",
    required=True,
    help="The host we will reach via ssh to run vivado, needs to provide ssh service and Vivado, without setting this, synthesis will run locally",
)
@click.option("--ssh-user", envvar=_SYNTH_SSH_USER_ENVVARS, required=True)
@click.option("--ssh-port", envvar=_SYNTH_SSH_PORT_ENVVARS, default=22, type=click.INT)
@click.option(
    "--target",
    envvar=_SYNTH_TARGET_ENVVARS,
    required=True,
    help="The target will determine the part number for vivado",
    type=click.Choice(TargetPlatforms),
)
@click.option(
    "--remote-working-dir",
    envvar=_SYNTH_REMOTE_WORKING_DIR_ENVVARS,
    required=True,
    help="Commands will be run from this directory on the remote host. The directory will be cleaned before each run, so you can still access any artifacts after each run. CAUTION: has not been tried with relative paths!",
)
@click.option(
    "--vivado-path",
    envvar=_SYNTH_VIVADO_PATH_ENVVARS,
    default="/tools/Xilinx/Vivado/2023.1/bin/vivado",
    help="The path to the vivado executable on the remote host",
)
@click.option("--quiet", is_flag=True)
def main(
    src_dir, host, ssh_user, ssh_port, target, remote_working_dir, vivado_path, quiet
):
    """Generate FPGA bitstreams remotely.

    The tool uploads files in SRC_DIR via ssh to a host,
    generates bitstream with vivado and downloads it
    together with reports.

    All options, except for --quiet, can be set from
    environment variables. Names for these variables
    are formed by prepending SYNTH_, e.g., --ssh-user
    becomes SYNTH_SSH_USER.
    """
    logging.basicConfig(
        level=logging.ERROR if quiet else logging.INFO,
        format="%(message)s",
    )
    _run_synthesis(
        src_dir,
        _OldSynthConfig(
            host=host,
            ssh_user=ssh_user,
            ssh_port=ssh_port,
            target=target,
            remote_working_dir=remote_working_dir,
            vivado_path=vivado_path,
            quiet=quiet,
        ),
    )


_tcl_script_content_tpl = Template("""
# run.tcl V3 - exits on any error

# Function to handle errors and exit Vivado
proc exit_on_error {errorMsg} {
    puts "Error: $errorMsg"
    exit 1
}

# Top-level catch block
if {[catch {

    # STEP#1: Setup design sources and constraints
    create_project ${project_name} ${remote_working_dir} -part $part_number -force
    add_files -fileset sources_1 ${remote_working_dir}/${srcs_dir}
    add_files -fileset constrs_1 -norecurse ${remote_working_dir}/${srcs_dir}/constraints.xdc
    update_compile_order -fileset sources_1

    # STEP#2: Run synthesis
    launch_runs synth_1 -jobs ${num_jobs}
    wait_on_run synth_1

    # STEP#3: Run implementation
    set_property STEPS.WRITE_BITSTREAM.ARGS.BIN_FILE true [get_runs impl_1]
    launch_runs impl_1 -to_step write_bitstream -jobs ${num_jobs}
    wait_on_run impl_1

} errorMsg]} {
    exit_on_error $errorMsg
}

# Exit cleanly if everything succeeds
exit
""")


def _create_srcs_archive(tmp_dir: Path, src_dir: Path) -> Path:
    result = tmp_dir / _SRCS_FILE_NAME
    with tar_open(result, "w:gz") as tar_file:
        for src_file in src_dir.glob("**/*.vhd"):
            tar_file.add(src_file, str(src_file.relative_to(src_dir)))

        for src_file in src_dir.glob("**/*.xdc"):
            tar_file.add(src_file, "constraints.xdc")
        os.chdir(tmp_dir)
        tar_file.add(tmp_dir / _TCL_SCRIPT_NAME, _TCL_SCRIPT_NAME)
    return result


def _write_tcl_script(
    tmp_dir: Path,
    project_name: str,
    part_number: str,
    remote_working_dir: str,
    num_jobs: int,
) -> None:
    (tmp_dir / _TCL_SCRIPT_NAME).write_text(
        _tcl_script_content_tpl.safe_substitute(
            remote_working_dir=remote_working_dir,
            srcs_dir=_SRCS_FILE_BASE_NAME,
            project_name=project_name,
            num_jobs=num_jobs,
            part_number=part_number,
        )
    )


def try_remove_recursively(connection, remote_path):
    quoted_rm = shlex.quote(f"rm -rf {remote_path}")
    connection.run(f"sh -c {quoted_rm}")


def _create_connection(
    host: str, ssh_user: str, ssh_port: int, quiet: bool
) -> _Connection:
    verbosity = Verbosity.ONLY_ERRORS if quiet else Verbosity.ALL
    if host == "":
        return _invokeConnection(_invContext(), verbosity=verbosity)
    return _fabConnectionWrapper(
        _fabConnection(host=host, user=ssh_user, port=ssh_port),
        verbosity,
    )


if __name__ == "__main__":
    main()
