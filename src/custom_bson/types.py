import os
import time
import struct

class ObjectId:
    """
    Custom implementation of MongoDB ObjectId.
    Consists of:
      - 4-byte timestamp
      - 5-byte machine identifier
      - 3-byte counter
    """
    _counter = 0

    def __init__(self, oid=None):
        if oid is None:
            self.oid = self.generate()
        elif isinstance(oid, bytes) and len(oid) == 12:
            self.oid = oid
        else:
            raise ValueError("ObjectId must be a 12-byte value.")

    @classmethod
    def generate(cls):
        timestamp = int(time.time()).to_bytes(4, "big")
        machine_id = os.urandom(5)
        counter = cls._counter.to_bytes(3, "big")
        cls._counter = (cls._counter + 1) % 0xFFFFFF
        return timestamp + machine_id + counter

    def __bytes__(self):
        return self.oid

    def __repr__(self):
        return f"ObjectId({self.oid.hex()})"
