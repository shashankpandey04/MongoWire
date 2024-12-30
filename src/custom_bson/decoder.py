import struct
from .types import ObjectId

async def decode(data):
    """
    Decodes a BSON document from bytes.
    """
    return await decode_document(data)

import struct

async def decode_document(bson_data):
    # Check that the BSON data is long enough to unpack the length
    if len(bson_data) < 4:
        raise ValueError("BSON data is too short to decode.")
    
    # Unpack the first 4 bytes to get the length of the full document
    length = struct.unpack("<i", bson_data[:4])[0]
    
    # Check if the full BSON document length matches the data length
    if len(bson_data) < length:
        raise ValueError(f"BSON data is incomplete. Expected {length} bytes, got {len(bson_data)}.")
    
    document = {}
    while data:
        element, data = await decode_element(data)
        document.update(element)
    return document


async def decode_element(data):
    """
    Decodes a single key-value pair from BSON.
    """
    element_type = data[0]
    data = data[1:]  # Remove element type byte
    key, data = data.split(b"\x00", 1)  # Split key from rest of data
    key = key.decode("utf-8")

    if element_type == 0x02:  # String
        length = struct.unpack("<i", data[:4])[0]
        value = data[4:4 + length - 1].decode("utf-8")  # Exclude null terminator
        return {key: value}, data[4 + length:]
    elif element_type == 0x10:  # int32
        value = struct.unpack("<i", data[:4])[0]
        return {key: value}, data[4:]
    elif element_type == 0x12:  # int64
        value = struct.unpack("<q", data[:8])[0]
        return {key: value}, data[8:]
    elif element_type == 0x01:  # double
        value = struct.unpack("<d", data[:8])[0]
        return {key: value}, data[8:]
    elif element_type == 0x03:  # Embedded document
        length = struct.unpack("<i", data[:4])[0]
        value = await decode_document(data[:length])
        return {key: value}, data[length:]
    elif element_type == 0x04:  # Array
        length = struct.unpack("<i", data[:4])[0]
        value = await decode_document(data[:length])
        return {key: list(value.values())}, data[length:]
    elif element_type == 0x07:  # ObjectId
        value = ObjectId(data[:12])
        return {key: value}, data[12:]
    elif element_type == 0x0A:  # Null
        return {key: None}, data
    else:
        raise TypeError(f"Unsupported BSON type: {element_type}")
