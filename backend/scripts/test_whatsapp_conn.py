import httpx
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def check_connection():
    EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL")
    EVOLUTION_INSTANCE_NAME = os.getenv("EVOLUTION_INSTANCE_NAME")
    EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")

    headers = {
        "apikey": EVOLUTION_API_KEY
    }

    print(f"Checking connection for instance: {EVOLUTION_INSTANCE_NAME} at {EVOLUTION_API_URL}")

    try:
        # Check connection state
        url = f"{EVOLUTION_API_URL}/instance/connectionState/{EVOLUTION_INSTANCE_NAME}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error checking connection: {e}")

if __name__ == "__main__":
    asyncio.run(check_connection())
