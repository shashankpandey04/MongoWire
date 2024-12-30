from .encoder import encode_document
from .decoder import decode_document
from .types import ObjectId

async def main():
    document = {
        "name": "Alice",
        "age": 25,
        "location": {"city": "NYC", "state": "NY"},
        "skills": ["Python", "MongoDB"],
        "_id": ObjectId()
    }

    bson_data = await encode_document(document)
    decoded_document = await decode_document(bson_data)

    print("Original:", document)
    print("Decoded:", decoded_document)

import asyncio
asyncio.run(main())
