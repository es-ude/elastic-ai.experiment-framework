import asyncio

from .. import RemoteControlProtocol, RemoteTaskController, TaskRegistry


class RemoteTestClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    async def run_task(self, msg: bytes):
        registry = TaskRegistry()

        result = {
            "chunks": [],
            "done": False,
            "last": False,
        }

        @registry.task(func_id=0, timeout=5.0)
        async def on_opened(ctx, send):
            await send(msg)

        async def on_chunk(ctx, data):
            result["chunks"].append(data)

        async def on_done(ctx):
            result["done"] = True

        async def on_last(ctx):
            result["last"] = True

        registry.get(0).on_data_chunk_received = on_chunk
        registry.get(0).on_finished = on_done
        registry.get(0).on_is_last = on_last

        protocol = RemoteControlProtocol()
        session = await protocol.connect_tcp(self.host, self.port)
        controller = RemoteTaskController(session, registry)

        try:
            (ctx,) = await asyncio.gather(
                controller.open_task(func_id=0),
            )

            await ctx.finished_event.wait()

            return ctx, result

        finally:
            await protocol.disconnect(session)
