import asyncio

from async_timeout import timeout

loop = asyncio.new_event_loop()
event = asyncio.Event()

time = 5


async def coro():
    global time
    async with timeout(time):
        if event.is_set():
            await event.wait()
        else:
            event.set()
        time = time + 1
        await asyncio.sleep(6)
        print("!!!!!")
        event.clear()


class Something:
    def __init__(self):
        self.event = asyncio.Event()

    async def __aenter__(self):
        try:
            if event.is_set():
                await event.wait()
            else:
                event.set()
        except:
            print("error")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        global time
        event.clear()
        time += 1

    async def coro(self):
        async with self:
            async with timeout(3):
                await asyncio.sleep(2)
                print(f"{time}")


x = Something()

loop.create_task(x.coro())
loop.create_task(x.coro())
loop.run_forever()
