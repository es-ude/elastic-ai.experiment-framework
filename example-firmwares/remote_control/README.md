# C implementation of the protocol

## Prerequisites

Before running anything you should enter the devenv enviroment with

```
devenv shell
```

or other means.

## Description

This part of the protocoll implements the protocoll on the embedded/remote site.

## How to compile

Currently there are two Cmake Presets for compilation, which should be executed in the location of this readme.


```
cmake --build --preset host-debug
cmake --build --preset pico-debug
```

### Host Debug

Used for the CI/CD Pipeline. Does use a TCP Server as a simulation of the external hardware.
Has a limited amount of functions because of this

### Pico Debug

Used for the flashing of the Pico ENV5 Hardware. 
Provides functions for handling FPGA features.
This build is used for the python eaixp CLI.



## How to add custom functions

Custom functions are given to the Firmware as an array containing "TaskDefinition" [defined here](src/lib/task.h).

```setup``` and ```teardown``` are called with the "openTask" and "closeTask" message type and allow custom handling of these cases.
```handle``` is called everytime a data packet arrives on the hardware addressed to the task ID.


The function needs to have the following signature:

```
void fn_name(TaskContext* task_context)
```

The [TaskContext](src/lib/task.h) contains the incoming and outgoing data interface. It also allows some other features like saving a pointer to a persistent data for implementing features like a state machine.




New functions should be added [here](src/user_code) following the already given examples.
The task definition id is given by the index in the array and can be used in the eaixp shell to run the task.


## Tests

The c side does conduct a few unit tests mainly on the ```host-debug``` preset for the CI/CD pipeline.
To run them locally, execute the following commands in the top level folder [here](../../):
```
devenv tasks run check:unit_tests_c
```
For system tests of the interaction between pc side and c side you can run
```
devenv tasks run check:system_tests
```
For testing pico firmware functions you can use
```
uv run pytest tests/fpga/test_fpga_remote_control.py
```

For further test implementations look into the [python documentation](../../src/elasticai/experiment_framework/README.md).

## Dependencies

This implmentation does import the elastic.ai-runtime repository for the compilation of the ENV5 firmware.