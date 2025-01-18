import asyncio
import struct

async def send_command(connection, bson_command):
    try:
        if asyncio.iscoroutine(bson_command):
            bson_command = await bson_command

        if not isinstance(bson_command, bytes):
            raise ValueError("bson_command must be a bytes-like object.")

        # MongoDB OP_MSG structure:
        # - Header (16 bytes)
        # - Flagbits (4 bytes)
        # - Section kind byte (1 byte)
        # - BSON document
        request_id = 1
        message_length = 21 + len(bson_command)  # 16 (header) + 4 (flagbits) + 1 (section) + BSON

        # Construct header
        header = struct.pack("<iiii", 
            message_length,    # Total message length
            request_id,        # Request ID
            0,                # Response To
            2013              # OP_MSG opcode
        )

        flags = struct.pack("<i", 0)  # Flagbits (4 bytes)
        section = b'\x00'  # Section kind byte (1 byte)

        # Construct the full message
        message = header + flags + section + bson_command
        
        print(f"Sending message length: {message_length}")
        print(f"BSON command length: {len(bson_command)}")
        
        # Send the message
        await connection.send(message)
        print("Message sent, waiting for response...")

        # Read the response header (16 bytes)
        response_header = await connection.receive(16)
        print(f"Received response header length: {len(response_header)}")
        
        if len(response_header) < 16:
            raise ValueError(f"Incomplete response header. Received {len(response_header)} bytes")

        # Parse response header
        resp_length, resp_req_id, resp_to, resp_code = struct.unpack("<iiii", response_header)
        print(f"Response length: {resp_length}, Request ID: {resp_req_id}, Response To: {resp_to}, Op Code: {resp_code}")

        # Read the rest of the response (including flagbits and sections)
        remaining_length = resp_length - 16
        print(f"Reading remaining {remaining_length} bytes...")
        
        response_body = b""
        while len(response_body) < remaining_length:
            chunk = await connection.receive(min(4096, remaining_length - len(response_body)))
            if not chunk:
                break
            response_body += chunk
            print(f"Received chunk of {len(chunk)} bytes")

        if len(response_body) < remaining_length:
            raise ValueError(f"Incomplete response body. Expected {remaining_length} bytes, got {len(response_body)}")

        print(f"Full response received: {len(response_header + response_body)} bytes")
        return response_header + response_body

    except Exception as e:
        print(f"Error in send_command: {str(e)}")
        raise