import argparse
import socket
import threading

from elasticai.experiment_framework.remote_control_v2.commands import Command
from elasticai.experiment_framework.remote_control_v2.header import Header
from elasticai.experiment_framework.remote_control_v2.message import Message
from elasticai.experiment_framework.remote_control_v2.remote_control_protocol import RemoteControlProtocol
from elasticai.experiment_framework.remote_control_v2.socket_io_stream import SocketIOStream
from elasticai.experiment_framework.remote_control_v2.constants import NUM_BYTES_FOR_ID 


def format_bytes(data: bytes) -> str:
    if not data:
        return "<empty>"
    return data.hex()


def format_message(msg: Message) -> str:
    header = msg.header
    lines = [
        f"command={header.command.name}",
        f"flags={header.flags}",
        f"msg_id={header.msg_id}",
        f"payload_len={header.payload_len}",
    ]

    if header.command == Command.OPEN_TASK:
        func_id = int.from_bytes(msg.payload[:1], byteorder="little", signed=False)
        payload = msg.payload[1:]
        lines.append(f"func_id={func_id}")
        lines.append(f"payload={format_bytes(payload)}")
    elif header.command == Command.DATA_CHUNK:
        if len(msg.payload) >= 2:
            task_id = int.from_bytes(msg.payload[:1], byteorder="little", signed=False)
            data_id = int.from_bytes(msg.payload[1:2], byteorder="little", signed=False)
            chunk = msg.payload[2:]
            lines.append(f"task_id={task_id}")
            lines.append(f"data_id={data_id}")
            lines.append(f"chunk={format_bytes(chunk)}")
        else:
            lines.append(f"payload={format_bytes(msg.payload)}")
    elif header.command == Command.RETURN:
        if len(msg.payload) >= 1:
            task_id = int.from_bytes(msg.payload[:1], byteorder="little", signed=False)
            lines.append(f"task_id={task_id}")
            if len(msg.payload) > 1:
                lines.append(f"payload={format_bytes(msg.payload[1:])}")
        else:
            lines.append(f"payload={format_bytes(msg.payload)}")
    else:
        lines.append(f"payload={format_bytes(msg.payload)}")

    return " | ".join(lines)


def recv_exact(conn: socket.socket, size: int) -> bytes:
    buffer = bytearray()
    while len(buffer) < size:
        chunk = conn.recv(size - len(buffer))
        if not chunk:
            raise ConnectionError("Connection closed while reading")
        buffer.extend(chunk)
    return bytes(buffer)


def read_message(conn: socket.socket) -> Message:
    header_bytes = recv_exact(conn, Header.SIZE)
    header = Header.from_bytes(header_bytes)
    payload = recv_exact(conn, header.payload_len)
    return Message.from_bytes(header_bytes + payload)


def hardware_server(host: str, port: int, ready: threading.Event) -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(1)
    ready.set()

    conn, addr = server.accept()
    print(f"Server accepted connection from {addr}")
    with conn:
        open_request = read_message(conn)
        print(f"Server received: {format_message(open_request)}")
        assert open_request.header.command == Command.OPEN_TASK, "Expected OPEN_TASK"

        task_id = 42
        task_id_bytes = task_id.to_bytes(1, "little")
        open_response = Message(Command.RETURN, task_id_bytes, msg_id=open_request.header.msg_id)
        conn.sendall(open_response.to_bytes())
        print(f"Server sent: {format_message(open_response)}")

        first_chunk = read_message(conn)
        print(f"Server received: {format_message(first_chunk)}")
        assert first_chunk.header.command == Command.DATA_CHUNK, "Expected first DATA_CHUNK"

        second_chunk = read_message(conn)
        print(f"Server received: {format_message(second_chunk)}")
        assert second_chunk.header.command == Command.DATA_CHUNK, "Expected second DATA_CHUNK"
        assert second_chunk.payload[2:] == b"", "Expected empty DATA_CHUNK payload"

        response_payload = first_chunk.payload[2:]
        response_chunk = Message(
            Command.DATA_CHUNK,
            task_id_bytes + (0).to_bytes(1, "little") + response_payload,
            msg_id=0,
        )
        conn.sendall(response_chunk.to_bytes())
        print(f"Server sent: {format_message(response_chunk)}")

        final_return = Message(Command.RETURN, b"", msg_id=0)
        conn.sendall(final_return.to_bytes())
        print(f"Server sent: {format_message(final_return)}")
        print("Server will close connection")


def hardware_client(host: str, port: int, func_id: int, args: bytes) -> None:
    print(f"Client connecting to {host}:{port} func_id={func_id} args={format_bytes(args)}")
    stream = SocketIOStream(host, port)
    with stream.connect() as device:
        protocol = RemoteControlProtocol(device)
        result = protocol.call_function(func_id=func_id, args=args)
        print(f"Client call_function returned: {format_bytes(result)}")


def run_demo(host: str, port: int, func_id: int, args: bytes) -> None:
    ready = threading.Event()
    server_thread = threading.Thread(target=hardware_server, args=(host, port, ready), daemon=True)
    server_thread.start()
    ready.wait(timeout=2.0)

    hardware_client(host, port, func_id, args)
    server_thread.join(timeout=2.0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hardware demo for remote control v2")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", default=8080, type=int)
    parser.add_argument("--mode", choices=["demo", "server", "client"], default="demo")
    parser.add_argument("--func-id", default=1, type=int)
    parser.add_argument("--args", default="", type=str, help="Function arguments as hex")
    args = parser.parse_args()

    payload = bytes.fromhex(args.args) if args.args else b""

    if args.mode == "server":
        ready = threading.Event()
        hardware_server(args.host, args.port, ready)
    elif args.mode == "client":
        hardware_client(args.host, args.port, args.func_id, payload)
    else:
        run_demo(args.host, args.port, args.func_id, payload)
