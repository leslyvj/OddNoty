import asyncio
import aiohttp
import sys

async def get_chat_id(token):
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    print(f"🔍 Checking for messages to your bot...")
    print(f"👉 Please send a message (e.g. 'hi') to your bot now: t.me/OddNotybot")
    
    async with aiohttp.ClientSession() as session:
        while True:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get("result", [])
                    if results:
                        chat_id = results[-1].get("message", {}).get("chat", {}).get("id")
                        user_name = results[-1].get("message", {}).get("chat", {}).get("first_name")
                        print(f"\n✅ Found it!")
                        print(f"User: {user_name}")
                        print(f"Your TELEGRAM_CHAT_ID is: {chat_id}")
                        print(f"\nPlease add this ID to your .env file.")
                        break
                else:
                    print(f"❌ Error: {resp.status}")
                    break
            await asyncio.sleep(2)

if __name__ == "__main__":
    TOKEN = "8785359235:AAHsUJ3j1G903HIOuBbAVWDW0u9VgrOeoeU"
    asyncio.run(get_chat_id(TOKEN))
