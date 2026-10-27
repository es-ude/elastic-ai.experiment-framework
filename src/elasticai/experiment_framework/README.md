# Python implementation of the protocol

## Project Structure

- The Python implemention of the protocol lies inside the `src/elasticai/experiment_framework\remote_control`: It contains all essential functionalities of the protocol in the for the PC side. The configuration file is here called constants.

- Beside it there is the `env5` folder. It propose some interfaces and use cases of the protocol for dealing with env5 hardware board.

- `tests` folder contains all  the tests that have been made throughout developement of the protocol


## Tools

The main tools used to manage packages and work synchronization are:

- uv:  to install, sync and running tests
- devenv/direnv:  to load projects dependency automantication


## CI
Tests are running  inside github workflow as the development evolves.

Of course, only tests that are independent of  hardware can be run. They are configured in the `devenv.nix` so that integrations, units and systems tests (against a TCP server endpoint) run.


## Current State

The protocol offers following features


- basic sending and receiving messages in a task based manner
- switchable acknowledgement and error crc error detection mechanisms
- transport layer abstraction(now 2 implementations: TCP and Serial)
- remote control interfaces both async and sync purposes

## Logging

In order to debug succintly, the transport layer(`message_io.py` and `io_stream.py`) contains debugging filters that enable logging of outgoing / incomming of string / raw bytes.

`src/elasticai/experiment_framework/remote_control/logging_config.py` contains necessary configuration.

For common use, string messages are enough, and tests  defauft for that as it is defined in the pytest options in `pyproject.toml` file as well as debug level.

However, for more detailed logs, `--show-raw` option can be passed to any pytest command as defined in the conftest file for filtering logging. 
e.g: 
```bash
uv run python -m pytest \
        tests/fpga/test_fpga_remote_control.py::test_fpga_flashing --show_raw

```
Alternatively, pytest cli options remains available as `--cli-log-level=INFO` to set the logs level to info


## Use Cases

First use case of the protocol concerns with interaction with env5 board:


Besides, a general purpose shell is available for dealing with and remote hardware (it should be extended/enhanced at convenience):

**Before entering the shell**
- make sure you are in the right virtual environment (`.devenv/state/venv/bin/python`)
- the device you use is supported / and flashed before (for now env5 boards are supported)
- you can flash with the command `eaxip remote flash`. It flashs it according to the configurations defined in `src/elasticai/experiment_framework/env5/flash_env5.py`

**Remote shell:**

- Accessing the shell: `eaxip remote shell`
It will probe for predefined devices and try to connect to the first found one the drives you in a shell prompt where you can enter you commands
    Options: `--debug`: display debug logs. At this point nur string formatted  incoming and outgoing from the transport layer will  be displayed
            `--raw`: display raw bytes in addition to string messages

Inside there you can use `help` to see the available commands and their use such as `open 0` (for openning a task of task definition id 0)


**Fpga shell**: 
Protocol allows running basic commands for interaction flashing and fpga firmware and interacting with it

fpga shell is built expecially for interaction with fpga such as flashing it, predictions or reading skeleton ID.

Usage: `eaxip fpga shell` to enter the shell (this connects to the harware and run the init task, kind of handshake task to exchange communication information such flashing-sector-size)

please use `eaxip fpga <command> --help` option for full syntax of every command. 
o
Then inside it you have the several commands such as

| command | purpose |
|--|--|
| power-on | powering on the fpga|
| power-off | powering off the fpga|
| read-skeleton-id| retrieving skeleton-id|
| upload *sector* *file_name*| upload bytes stream|
| predict *output_len* *input*| use the flashed fpga firmware to predict |

These commands only make sense after having entered the shell and are not meant be used directly in terminal.

*file_name* can be passed  either in a absolut or relativ way depending on your current working direction(where you run the command)


**Caveats**

- Ack mechanism is needed for uploading huge amount of byte streams
- resetting fpga manually does not always reset its hardware_id even using clear-flashing
- this documentation relies on the parent branch which is currently not in main is not ready and meant to be merged to main at it is. however, it propose useful ways for interaction with the remote remote control. That is it can be improved or splitted before merging.


