import asyncio
from scanner.client import WekanClient, WekanClientConfig

async def test_authentication():
    base_url = "http://10.0.100.141:80"
    token = "BVLb20pWuLexuJenyH9BiM0BMI5HowYWN4U0-eY1ZTH"
    endpoint = "/users/wTwRSy8c5EY6LBrKb/boards"

    config = WekanClientConfig(base_url=base_url, token=token)

    try:
        async with WekanClient(config) as client:
            print(f"Attempting to connect to {base_url} and fetch {endpoint}...")
            response = await client.get(endpoint)
            print(f"Status Code: {response.status_code}")
            print(f"Response JSON: {response.json}")

            if response.status_code == 200:
                print("Authentication successful!")
            else:
                print("Authentication failed.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(test_authentication())