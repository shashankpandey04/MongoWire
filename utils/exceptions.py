class MongoWireException(Exception):
    """Base exception for MongoWire."""

class ConnectionError(MongoWireException):
    """Raised when there is a connection issue."""
