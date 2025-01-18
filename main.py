from src.connection.client import MongoClient
import asyncio

async def main():
    uri = "mongodb://localhost:27017/"
    client = MongoClient(uri)
    try:
        print("Connecting to MongoDB...")
        await client.connect()

        print("\nListing databases...")
        response = await client.command({"listDatabases": 1})
        print("\nDatabases response:", response)

    except Exception as e:
        print(f"Error in main: {e}")
        import traceback
        print(traceback.format_exc())
    finally:
        print("\nClosing connection...")
        await client.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Unhandled exception: {e}")
