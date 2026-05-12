import asyncio
import logging
import socket
import threading
import sys
from elasticai.experiment_framework.remote_control.commands import Command
from elasticai.experiment_framework.remote_control.constants import HEADER_SIZE, NUM_BYTES_FOR_ID
from elasticai.experiment_framework.remote_control.flags import Flags
from elasticai.experiment_framework.remote_control.header import Header
from elasticai.experiment_framework.remote_control.message import Message
from elasticai.experiment_framework.remote_control.basic_usage import main as run_client


def run_server(host: str, port: int, ready: threading.Event) -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(1)
    ready.set()
    print("Waiting for Connection")

    conn, _ = server.accept()
    with conn:
        msg = _read_message(conn)
        print(f"[server] rx OPEN_TASK tid={msg.header.transaction_id}")

        conn.sendall(Message(Command.ACK, b"", transaction_id=msg.header.transaction_id).to_bytes())
        print(f"[server] tx ACK tid={msg.header.transaction_id}")

        chunk = _read_message(conn)
        data  = chunk.payload[NUM_BYTES_FOR_ID:]  
        print(f"[server] rx DATA_CHUNK data={data}")

        reply_payload = data
        conn.sendall(Message(Command.DATA_CHUNK, reply_payload,flags=Flags(is_last=True).to_byte() , transaction_id=chunk.header.transaction_id).to_bytes())
        print(f"[server] tx DATA_CHUNK echo={data}")

        conn.sendall(Message(Command.RETURN, b"",  transaction_id=chunk.header.transaction_id).to_bytes())
        print(f"[server] tx RETURN (finished)")


def _read_message(conn: socket.socket) -> Message:
    header_bytes = _recv_exact(conn, HEADER_SIZE)
    header       = Header.from_bytes(header_bytes)
    print(f"received header = {header_bytes} {header}")
    
    payload      = _recv_exact(conn, header.payload_len)
    print(f"received paylod = {payload} {header.payload_len}")

    return Message.from_bytes(header_bytes + payload)


def _recv_exact(conn: socket.socket, size: int) -> bytes:
    buf = bytearray()
    while len(buf) < size:
        chunk = conn.recv(size - len(buf))
        if not chunk:
            raise ConnectionError("connection closed")
        buf.extend(chunk)
    return bytes(buf)



def main():
    
    logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",)
     
    mode = sys.argv[1] if len(sys.argv) > 1 else "demo"

    if mode == "server":
        event = threading.Event()
        run_server("127.0.0.1", 8080, event)

    elif mode == "client":
        asyncio.run(run_client())

    else:                                        
        ready = threading.Event()
        print("set server")
        
        threading.Thread(target=run_server, args=("127.0.0.1", 8080, ready), daemon=True).start()
        ready.wait()
        asyncio.run(run_client())

if __name__ == "__main__":
    main()