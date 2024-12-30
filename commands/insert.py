async def insert(client, collection, documents):
    command = {
        "insert": collection,
        "documents": documents
    }
    return await client.command(command)
