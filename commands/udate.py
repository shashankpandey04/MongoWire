async def update(client, collection, updates):
    command = {
        "update": collection,
        "updates": updates
    }
    return await client.command(command)
