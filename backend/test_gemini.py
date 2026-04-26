import asyncio
import os
from google import genai
from core.config import settings

async def test():
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    
    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents="Hello",
            config={
                "system_instruction": "You are a bot",
                "temperature": 0.7,
                "max_output_tokens": 800
            }
        )
        print("Success!")
        print(response.text)
    except Exception as e:
        print(f"Exception Type: {type(e)}")
        print(f"Exception String: {str(e)}")

asyncio.run(test())
