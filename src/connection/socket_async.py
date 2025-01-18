import asyncio

class AsyncSocket:
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer

    @classmethod
    async def connect(cls, host, port):
        reader, writer = await asyncio.open_connection(host, port)
        return cls(reader, writer)

    async def send(self, data):
        self.writer.write(data)
        await self.writer.drain()

    async def receive(self, buffer_size=4096):
        data = await self.reader.read(buffer_size)
        return data

    async def close(self):
        if not self.writer.is_closing():
            self.writer.close()
            await self.writer.wait_closed()

