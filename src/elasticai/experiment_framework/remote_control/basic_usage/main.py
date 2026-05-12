import asyncio

from elasticai.experiment_framework.remote_control.remote_control_protocol import RemoteControlProtocol
from elasticai.experiment_framework.remote_control.remote_task_controller import RemoteTaskController


from elasticai.experiment_framework.remote_control.task_registry import TaskRegistry

registry = TaskRegistry()

@registry.task(func_id=1, need_ack=True, timeout=5.0)
async def on_inference_opened(ctx, send):
    await send(b"input_data") 

async def on_inference_chunk(ctx, data):
    print(f"verified result: {data}")

async def on_inference_done(ctx):
    print(f"all data: {ctx.received_data}")

async def on_last_chunk(ctx):
    print(f"The last chunk is recived")

registry.get(1).on_data_chunk_received = on_inference_chunk
registry.get(1).on_finished   = on_inference_done
registry.get(1).on_is_last   = on_last_chunk

@registry.task(func_id=2, need_ack=False)
async def on_stream_opened(ctx, send):
    for i in range(10):
        await send(f"frame_{i}".encode())  

async def main():
    protocol   = RemoteControlProtocol()
    session    = await protocol.connect_tcp("127.0.0.1", 8080)
    controller = RemoteTaskController(session, registry)

    try:
        ctx1, = await asyncio.gather(
            controller.open_task(func_id=1),
        )

        await asyncio.gather(
        ctx1.finished_event.wait(),
        )
    except TimeoutError as e:
        print(f"task timed out: {e}")
        await protocol.disconnect(session)

    except ConnectionError as e:
        print(f"connection lost: {e}")
