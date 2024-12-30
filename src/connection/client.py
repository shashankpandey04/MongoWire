from src.connection.protocol import send_command
from src.custom_bson.encoder import encode
from src.custom_bson.decoder import decode

class MongoClient:
    def __init__(self, host='localhost', port=27017):
        self.host = host
        self.port = port
        self.connection = None

    async def connect(self):
        from .socket_async import AsyncSocket
        self.connection = await AsyncSocket.connect(self.host, self.port)
        print(f"Connected to {self.host}:{self.port}")

    async def command(self, command):
        if not self.connection:
            raise ConnectionError("Not connected to MongoDB.")
        command_bson = await encode(command)
        response = await send_command(self.connection, command_bson)
        return await decode(response)

    async def close(self):
        if self.connection:
            await self.connection.close()
