async def find(client, collection, filter_doc):
    command = {
        "find": collection,
        "filter": filter_doc
    }
    return await client.command(command)
