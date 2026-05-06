# Embedded Remote Control


This directory contains the embedded-side remote control runtime for the Elastic AI experiment framework. It implements a simple local TCP-based command protocol with task management, message framing, and a callable function table.

The tool opens a server on Port 8080 and listens there for a connection using the specified protocol.

## Implemented Message Types and other ToDos

- [x] `OPEN_TASK` (`0x01`) - Request to start a new task.
- [ ] `CLOSE_TASK` (`0x02`) - Request to close a task.
- [ ] `RETURN` (`0x03`) - Response or function return payload.
- [x] `DATA_CHUNK` (`0x04`) - Transfer chunked data.
- [ ] `ACK` (`0x05`) - Acknowledge receipt.
- [ ] `NACK` (`0x06`) - Negative acknowledgment.
- [ ] `HANDSHAKE` (`0x07`) - Optional handshake message.

- [ ] Memory Managment (Free)
- [x] Move Testcase in seperate files 

## Components

- `embedded_protocol.c` - Implements the frame protocol, task queuing, worker thread processing, and server/client threads.
- `sockets.c` / `sockets.h` - TCP server/client helpers for establishing and accepting connections.
- `embedded_functions.c` / `embedded_functions.h` - Defines the functions that can be invoked remotely and the dispatcher that executes them by function ID.
- `task_manager.c` / `task_manager.h` - Task pool management, task queuing, and task lifecycle handling.
- `frame_builder.c` / `frame_builder.h` - Builder functions for creating specific frame types 
- `enums.h` - Protocol constants such as message types and task/stream status flags.
- `frame.h` - Frame structure definitions for the protocol.
- `CMakeLists.txt` - Build entrypoint for the embedded remote control executable.
- `embedded_test.c` - Runs a test client which tests some message scenarios

## Protocol Overview

The embedded-side protocol is based on fixed-size frame headers and variable payloads.

Frame header fields:
- `start_byte` - Always `0xAA` to identify frame start.
- `message_type` - One of the message types defined in `enums.h`.
- `flags` - Reserved for future use.
- `msg_id` - A per-message identifier.
- `payload_len` - Number of payload bytes following the header.

Message types:
- `OPEN_TASK` (`0x01`) - Request to start a new task.
- `CLOSE_TASK` (`0x02`) - Request to close a task.
- `RETURN` (`0x03`) - Response or function return payload.
- `DATA_CHUNK` (`0x04`) - Transfer chunked data.
- `ACK` (`0x05`) - Acknowledge receipt.
- `NACK` (`0x06`) - Negative acknowledgment.
- `HANDSHAKE` (`0x07`) - Optional handshake message.

## Architecture

The runtime uses three main thread roles:

- `server_thread` - Accepts incoming TCP connections and reads frames from the host.
- `sending_thread` - Sends queued outgoing frames back to the host.
- `tasks_thread` - Processes queued tasks by executing the requested embedded functions.

A simple multi-producer / single-consumer queue is used for both outgoing messages and task execution.

## Callable Functions

Remote invocations are dispatched through a function table in `embedded_functions.c`.

Current functions:
- `send_mirror_reply` - Echoes back the input payload.
- `func1` - Placeholder remote function with no output.

Function IDs are based on the array index in `function_table[]`.

## Build

From this directory:

```bash
mkdir -p build
cd build
cmake ..
cmake --build .
```

This produces the `embedded_remote_control` executable.

## Run

The program starts the embedded-side server and processing threads. 

Example:

```bash
./embedded_remote_control 
```

The embedded-side server listens on port `8080` and waits for a host connection.


## Tests

To test the sending of text back and forth build the test c file with cmake in the tests folder:

```bash
mkdir -p build
cd build
cmake ..
cmake --build .
```

and run it 

```bash
./embedded_remote_control_test
```

## Notes

- The current implementation is intended as a prototype.
