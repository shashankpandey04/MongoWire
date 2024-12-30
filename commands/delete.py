async def delete(client, collection, deletes):
    command = {
        "delete": collection,
        "deletes": deletes
    }
    return await client.command(command)
