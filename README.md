# elastic-ai.Experiment-Framework

A framework to support you in performing experiments with the elastic-ai.Hardware (eai.Hardware) and related setups.

## Features

- [ ] Stream data to elastic-ai.Hardware
- [ ] Stream data from elastic-ai.Hardware
- [ ] Automatically synthesize HW Accelerators that were created using the the elastic-ai.Creator
- [ ] Parse Vivado reports into python dictionaries
- [ ] Call custom functions on the elastic-ai.Hardware from python scripts
- [ ] Measure Power/Latency for different workloads
- [ ] Perform different types of inferences on the HW accelerators from the elastic-ai.Creator via python API
- [ ] Push multiple bitstreams with FPGA configurations to eai.Hardware flash chips
- [ ] Load specific bitstreams from flash to FPGA
- [ ] Communication via USB/UART
- [ ] Communication via TCP/Lightweight IP
- [ ] Parse headers with c structs to automatically generate corresponding python types and methods to construct them from received data
- [ ] Parse headers with c functions to automatically generate corresponding python stubs for remote procedure calls to the eai.Hardware
- [x] Semi-automatic synthesis  (info via `eaixp synth --help`) with
  - [x] Vivado local
  - [x] Vivado remote

## Quick Start

```bash
$ uvx --from "git+https://github.com/es-ude/elastic-ai.experiment-framework.git" eaixp --help
```
or 
```bash
$ uv tool install "git+https://github.com/es-ude/elastic-ai.experiment-framework.git"
$ uv tool run eaixp --help
```
or
```bash
$ pip install "git+https://github.com/es-ude/elastic-ai.experiment-framework.git"
$ eaixp --help
```



### Communicating with the elastic node via elasticai runtime

1. Checkout the [elastic ai runtime](https://github.com/es-ude/elastic-ai.runtime.enV5/)
   ```bash
    $ git clone git@github.com:es-ude/elastic-ai.runtime.enV5.git
    $ cd elastic-ai.runtime.env5
   ```
2. build the firmware either directly (make sure to have gcc-arm-noneabi available)
   ```bash
    $ cmake --preset env5_rev2_release
    $ cmake --build --preset env5_rev2_release
   ```
   alternatively with devenv
  ```bash
   $ devenv tasks run -m before build
  ```
3. set the hardware to bootloader mode, e.g., by cycling power, while holding the boot button
4. copy the firmware to the device, e.g.,
  ```bash
  $ cp build/env5_rev2_release/test\
    /hardware/TestUsbProtocol/HardwareTestUsbProtocol.uf2\
    /var/Volume/RP2
  ```
5. run the remote control
  ```bash
  uv run python -m elasticai.tester.remote_control -h
  ```
