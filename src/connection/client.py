from src.connection.protocol import send_command
from src.custom_bson.encoder import encode
from src.custom_bson.decoder import decode

# client.py
import platform
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse
import hashlib
import base64
import os

class MongoClient:
    def __init__(self, uri='mongodb://localhost:27017/'):
        self.uri = uri
        self.host = 'localhost'
        self.port = 27017
        self.username = None
        self.password = None
        self.connection = None
        self.parse_uri()

    def parse_uri(self):
        """Parse the MongoDB URI and extract connection details."""
        parsed = urlparse(self.uri)
        self.host = parsed.hostname
        self.port = parsed.port or 27017
        self.username = parsed.username
        self.password = parsed.password

        # Extract database from the URI path or default to 'admin'
        self.database = parsed.path.lstrip("/") or "admin"

        # Format the username as <database>.<username>
        if self.username:
            self.username = f"{self.database}.{self.username}"

    async def authenticate(self):
        """Authenticate using SCRAM-SHA-256."""
        if not self.username or not self.password:
            raise ValueError("Username and password are required for authentication.")

        # Step 1: Create client nonce
        client_nonce = base64.b64encode(os.urandom(24)).decode("utf-8")
        client_first_bare = f"n={self.username},r={client_nonce}"
        client_first_message = f"n,,{client_first_bare}"

        # Step 2: Send the first SCRAM message to the server
        response = await self.command({
            "saslStart": 1,
            "mechanism": "SCRAM-SHA-1",
            "payload": base64.b64encode(client_first_message.encode("utf-8")).decode("utf-8"),
            "autoAuthorize": 1
        })
        print(f"saslStart response: {response}")

        if "payload" not in response:
            raise ValueError(f"saslStart failed: {response.get('errmsg', 'Unknown error')}")

        server_payload = base64.b64decode(response["payload"]).decode("utf-8")
        server_data = self.parse_scram_payload(server_payload)
        server_nonce = server_data["r"]
        salt = base64.b64decode(server_data["s"])
        iterations = int(server_data["i"])

        if not server_nonce.startswith(client_nonce):
            raise ValueError("Server nonce does not start with client nonce.")

        # Step 3: Generate salted password
        salted_password = self.pbkdf2(self.password.encode("utf-8"), salt, iterations)

        # Step 4: Generate client and server proofs
        client_final_no_proof = f"c=biws,r={server_nonce}"
        auth_message = f"{client_first_bare},{server_payload},{client_final_no_proof}"
        client_proof, server_signature = self.calculate_proofs(salted_password, auth_message)

        client_final_message = f"{client_final_no_proof},p={client_proof}"
        final_response = await self.command({
            "saslContinue": 1,
            "payload": base64.b64encode(client_final_message.encode("utf-8")).decode("utf-8"),
            "conversationId": response["conversationId"]
        })

        if not final_response.get("done", False):
            raise ValueError("Authentication failed: SCRAM handshake not completed.")

        server_signature_received = base64.b64decode(self.parse_scram_payload(base64.b64decode(final_response["payload"]).decode("utf-8"))["v"])
        if server_signature != server_signature_received:
            raise ValueError("Server signature verification failed.")

        print("Authentication successful!")

    def pbkdf2(self, password, salt, iterations, dklen=32, hash_func="sha256"):
        """Derive a key using PBKDF2."""
        import hashlib
        import hmac
        from functools import partial

        if hash_func.lower() == "sha256":
            hash_func = hashlib.sha256
        elif hash_func.lower() == "sha1":
            hash_func = hashlib.sha1
        else:
            raise ValueError("Unsupported hash function.")

        h = hmac.new
        mac = h(password, salt + b"\x00\x00\x00\x01", hash_func).digest()
        result = bytearray(mac)
        for _ in range(1, iterations):
            mac = h(password, mac, hash_func).digest()
            result = bytearray(a ^ b for a, b in zip(result, mac))
        return bytes(result)

    def calculate_proofs(self, salted_password, auth_message):
        """Calculate client and server proofs."""
        import hmac
        client_key = hmac.new(salted_password, b"Client Key", hashlib.sha256).digest()
        stored_key = hashlib.sha256(client_key).digest()
        client_signature = hmac.new(stored_key, auth_message.encode("utf-8"), hashlib.sha256).digest()
        client_proof = base64.b64encode(bytes(a ^ b for a, b in zip(client_key, client_signature))).decode("utf-8")

        server_key = hmac.new(salted_password, b"Server Key", hashlib.sha256).digest()
        server_signature = hmac.new(server_key, auth_message.encode("utf-8"), hashlib.sha256).digest()

        return client_proof, server_signature

    def parse_scram_payload(self, payload):
        """Parse SCRAM payload into a dictionary."""
        return dict(item.split("=", 1) for item in payload.split(","))

    async def connect(self):
        from .socket_async import AsyncSocket
        self.connection = await AsyncSocket.connect(self.host, self.port)
        print(f"Connected to {self.host}:{self.port}")
        
        handshake = {
                "isMaster": 1,
                "client": {
                    "application": {"name": "PyMongoClient"},
                    "driver": {"name": "PyMongo", "version": "1.0"},
                    "os": {
                        "type": platform.system().lower(),
                        "name": platform.system(),
                        "architecture": platform.machine(),
                        "version": platform.version()
                    },
                    "platform": f"Python {sys.version}"
                },
                "compression": [],
                "protocol_version": 1,
                "$db": "admin"
            }
            
        if self.username:
            handshake["saslSupportedMechs"] = f"{self.username}"

        print("Sending handshake...")
        handshake_response = await self.command(handshake)
        print(f"Handshake response: {handshake_response}")

        # Authenticate after handshake
        if self.username and self.password:
            await self.authenticate()

    async def command(self, command):
        if not self.connection:
            raise ConnectionError("Not connected to MongoDB.")
            
        if "$db" not in command:
            command["$db"] = "admin"
            
        print(f"Encoding command: {command}")
        command_bson = await encode(command)
        print(f"Sending command of length: {len(command_bson)}")
        
        response = await send_command(self.connection, command_bson)
        print(f"Received response of length: {len(response)}")
        
        # Skip header (16 bytes), flagbits (4 bytes), and section kind byte (1 byte)
        decoded = await decode(response[21:])
        print(f"Decoded response: {decoded}")
        return decoded

    async def close(self):
        if self.connection:
            await self.connection.close()
            self.connection = None