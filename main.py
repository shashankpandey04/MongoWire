from src.connection.client import MongoClient
import asyncio


async def main():
    client = MongoClient()
    try:
        await client.connect()
        response = await client.command({"listDatabases": 1})
        print("Databases response:", response)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
