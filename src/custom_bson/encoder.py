import struct
from .types import ObjectId

async def encode(document):
    """
    Encodes a Python dictionary into BSON.
    """
    return await encode_document(document)

async def encode_document(document):
    """
    Encodes a Python dictionary into BSON.
    """
    encoded = b""
    for key, value in document.items():
        encoded += await encode_element(key, value)

    # Add document length + null terminator
    length = len(encoded) + 5  # 4 bytes for length + 1 byte for null terminator
    return struct.pack("<i", length) + encoded + b"\x00"


async def encode_element(key, value):
    """
    Encodes a single key-value pair into BSON.
    """
    key_bytes = key.encode("utf-8") + b"\x00"
    if isinstance(value, str):
        value_bytes = await encode_string(value)
        return b"\x02" + key_bytes + value_bytes
    elif isinstance(value, int):
        if -(2**31) <= value <= (2**31) - 1:
            value_bytes = struct.pack("<i", value)
            return b"\x10" + key_bytes + value_bytes  # BSON int32
        else:
            value_bytes = struct.pack("<q", value)
            return b"\x12" + key_bytes + value_bytes  # BSON int64
    elif isinstance(value, float):
        value_bytes = struct.pack("<d", value)
        return b"\x01" + key_bytes + value_bytes  # BSON double
    elif isinstance(value, list):
        value_bytes = await encode_array(value)
        return b"\x04" + key_bytes + value_bytes
    elif isinstance(value, dict):
        value_bytes = await encode_document(value)
        return b"\x03" + key_bytes + value_bytes
    elif isinstance(value, ObjectId):
        value_bytes = bytes(value)
        return b"\x07" + key_bytes + value_bytes
    elif value is None:
        return b"\x0A" + key_bytes  # BSON null
    else:
        raise TypeError(f"Unsupported BSON type: {type(value)}")


async def encode_string(value):
    """
    Encodes a string into BSON.
    """
    value_bytes = value.encode("utf-8")
    length = len(value_bytes) + 1  # Add 1 for null terminator
    return struct.pack("<i", length) + value_bytes + b"\x00"


async def encode_array(array):
    """
    Encodes a Python list into BSON.
    """
    encoded = b""
    for idx, value in enumerate(array):
        encoded += await encode_element(str(idx), value)

    # Add array length + null terminator
    length = len(encoded) + 5  # 4 bytes for length + 1 byte for null terminator
    return struct.pack("<i", length) + encoded + b"\x00"
