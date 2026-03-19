import tarfile
from .verbosity import Verbosity
from dataclasses import dataclass
import logging
from fabric import Connection as _fabConnection
import click
from enum import StrEnum, auto
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


class TargetPlatforms(StrEnum):
    env5 = auto()


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
class SynthesisConfig:
    src_dir: Path
    host: str
    ssh_user: str
    ssh_port: int
    target: TargetPlatforms
    remote_working_dir: str
    vivado_path: str
    quiet: bool = False


def _run_synthesis(config: SynthesisConfig) -> Path:
    connection = _create_connection(
        config.host, config.ssh_user, config.ssh_port, config.quiet
    )

    logger.info("connecting to %s as %s", config.host, config.ssh_user)
    logger.info("uploading %s", config.src_dir.absolute())
    src_dir = config.src_dir.absolute()
    target_file = src_dir.parent.absolute() / "vivado_run_results.tar.gz"
    project_name = "AI_Accel"

    if target_file.exists():
        logger.info(
            "skipping %s because target file %s already exists",
            src_dir,
            target_file.absolute(),
        )
        return target_file
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
            try_remove_recursively(connection, f"{config.remote_working_dir}/{name}")
        connection.run(f"mkdir -p {config.remote_working_dir}/{_SRCS_FILE_BASE_NAME}")
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
            str(src_dir.parent.absolute() / "vivado_run_results.tar.gz"),
        )
    return target_file


def run_synthesis(src_dir: Path, config: SynthesisConfig | None = None) -> Path:
    """Synthesize with vivado. Loads config from env if not present.

    Uploads the vhdl files in `src_dir` to a remote, runs
    the synthesis with vivado and downloads the results to
    a file called `vivado_run_results.tar.gz`. This file
    is unpacked afterwards and we return the path to the
    contained binfile.

    The archive additionally contains log files.
    To run the synthesis locally, use `config.host = ""`.

    See the corresponding command line tool's help message
    via `eaixp synth --help` for documentation of the other
    `config` parameters.
    """
    if config is None:
        config = _load_synthesis_config_from_env(src_dir)

    _run_synthesis(config)

    tar_path = src_dir.parent / "vivado_run_results.tar.gz"
    if not tar_path.exists():
        raise RuntimeError(f"Synthesis output archive not found at {tar_path}")

    extract_dir = src_dir.parent / "vivado_results"
    extract_dir.mkdir(exist_ok=True)
    with tarfile.open(tar_path, "r:gz") as archive:
        archive.extractall(extract_dir)

    binfiles = sorted(extract_dir.glob("results/impl/*.bin"))
    if not binfiles:
        raise RuntimeError("No .bin file found in Vivado synthesis results")
    return binfiles[0]


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
        SynthesisConfig(
            src_dir=src_dir,
            host=host,
            ssh_user=ssh_user,
            ssh_port=ssh_port,
            target=target,
            remote_working_dir=remote_working_dir,
            vivado_path=vivado_path,
            quiet=quiet,
        )
    )


def _load_synthesis_config_from_env(src_dir: Path) -> SynthesisConfig:
    return SynthesisConfig(
        src_dir=src_dir,
        host=os.environ.get("SYNTH_SERVER", os.environ.get("SYNTH_HOST", "")),
        ssh_user=os.environ["SYNTH_SSH_USER"],
        ssh_port=int(os.environ.get("SYNTH_SSH_PORT", "22")),
        target=TargetPlatforms(os.environ["SYNTH_TARGET"]),
        remote_working_dir=os.environ["SYNTH_REMOTE_WORKING_DIR"],
        vivado_path=os.environ.get(
            "SYNTH_VIVADO_PATH", "/tools/Xilinx/Vivado/2023.1/bin/vivado"
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
