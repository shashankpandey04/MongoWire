import os
import hmac
import hashlib
import base64
from secrets import token_urlsafe


async def authenticate(client, username, password, database="admin"):
    """
    Implements MongoDB's SCRAM-SHA-256 authentication mechanism.
    :param client: MongoClient instance (connected).
    :param username: Username for authentication.
    :param password: Password for authentication.
    :param database: The authentication database (default is "admin").
    """
    # Step 1: Start handshake
    mechanism = "SCRAM-SHA-256"
    client_nonce = token_urlsafe(24)  # Generate a secure client nonce
    sasl_start_cmd = {
        "saslStart": 1,
        "mechanism": mechanism,
        "payload": _base64_encode(f"n,,n={username},r={client_nonce}".encode("utf-8")),
        "autoAuthorize": 1,
    }

    sasl_start_response = await client.command(sasl_start_cmd, database=database)

    # Extract server details from the response
    server_payload = _base64_decode(sasl_start_response["payload"])
    parsed_server_data = _parse_payload(server_payload)
    server_nonce = parsed_server_data["r"]
    salt = parsed_server_data["s"]
    iterations = int(parsed_server_data["i"])

    # Ensure server nonce includes client nonce
    if not server_nonce.startswith(client_nonce):
        raise ValueError("Server nonce does not include client nonce.")

    # Step 2: Compute client proof
    salted_password = _hi(password, _base64_decode(salt), iterations)
    client_key = _hmac(salted_password, b"Client Key")
    stored_key = hashlib.sha256(client_key).digest()

    auth_message = f"n={username},r={client_nonce},{server_payload},c=biws,r={server_nonce}".encode(
        "utf-8"
    )
    client_signature = _hmac(stored_key, auth_message)
    client_proof = _xor(client_key, client_signature)

    # Create client-final-message
    client_final_message = f"c=biws,r={server_nonce},p={_base64_encode(client_proof)}"
    sasl_continue_cmd = {
        "saslContinue": 1,
        "conversationId": sasl_start_response["conversationId"],
        "payload": _base64_encode(client_final_message.encode("utf-8")),
    }

    sasl_continue_response = await client.command(sasl_continue_cmd, database=database)

    # Step 3: Verify server signature
    server_payload = _base64_decode(sasl_continue_response["payload"])
    parsed_server_data = _parse_payload(server_payload)
    server_key = _hmac(salted_password, b"Server Key")
    expected_server_signature = _hmac(server_key, auth_message)

    if parsed_server_data["v"] != _base64_encode(expected_server_signature):
        raise ValueError("Server signature validation failed.")

    # Authentication successful if no exception raised
    return sasl_continue_response


# Utility Functions


def _hmac(key, message):
    """
    Computes an HMAC using SHA-256.
    """
    return hmac.new(key, message, hashlib.sha256).digest()


def _hi(password, salt, iterations):
    """
    Implements PBKDF2 with HMAC-SHA-256.
    Derives a salted password using the salt and iteration count.
    """
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)


def _xor(bytes1, bytes2):
    """
    Performs XOR operation on two byte sequences.
    """
    return bytes(b1 ^ b2 for b1, b2 in zip(bytes1, bytes2))


def _base64_encode(data):
    """
    Base64 encodes data.
    """
    return base64.standard_b64encode(data).decode("utf-8")


def _base64_decode(data):
    """
    Base64 decodes data.
    """
    return base64.standard_b64decode(data)


def _parse_payload(payload):
    """
    Parses a SCRAM payload string into a dictionary.
    Example:
      Input: "r=server_nonce,s=salt,i=10000"
      Output: {"r": "server_nonce", "s": "salt", "i": "10000"}
    """
    return dict(item.split("=", 1) for item in payload.decode("utf-8").split(","))
