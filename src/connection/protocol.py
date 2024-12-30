import asyncio
import struct

async def send_command(connection, bson_command):
    try:
        # Check if bson_command is a coroutine and await it if necessary
        if asyncio.iscoroutine(bson_command):
            bson_command = await bson_command()

        # Ensure bson_command is in bytes
        if not isinstance(bson_command, bytes):
            raise ValueError("bson_command must be a bytes-like object.")

        message_length = 16 + len(bson_command)
        header = struct.pack("<iiii", message_length, 0, 0, 2013)  # MongoDB OP_MSG
        message = header + bson_command
        
        print(f"Sending message: {message}")  # Debugging line

        # Write the message to the connection
        if connection.writer:
            connection.writer.write(message)
            await connection.writer.drain()
        else:
            raise ValueError("Connection writer is None.")

        # Debugging: Ensure the message is written
        print("Message sent to MongoDB.")

        # Read the first 4 bytes from the response to get the length
        header = await connection.reader.read(4)
        print(f"Received header: {header}")  # Debugging line

        if len(header) < 4:
            raise ValueError(f"Incomplete response header from MongoDB. Received {len(header)} bytes.")
        
        full_length = struct.unpack("<i", header)[0]  # Get the full message length from the header
        remaining_length = full_length - 4  # Subtract header length from total length

        # Read the rest of the response data
        response = await connection.reader.read(remaining_length)
        if len(response) < remaining_length:
            raise ValueError(f"Incomplete response data. Expected {remaining_length} bytes, got {len(response)} bytes.")
        
        print(f"Received response: {response}")  # Debugging line
        return header + response  # Return the full response including header and data
    except Exception as e:
        print(f"Error in send_command: {e}")  # Debugging line
        raise
