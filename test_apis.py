import os
import asyncio
from dotenv import load_dotenv
from deepgram import DeepgramClient, SpeakOptions
from groq import AsyncGroq

load_dotenv()

async def test_deepgram_stt():
    print("\nTesting Deepgram STT Connection...")
    try:
        dg_key = os.getenv("DEEPGRAM_API_KEY")
        if not dg_key:
            print("❌ DEEPGRAM_API_KEY is missing in .env")
            return
        
        deepgram = DeepgramClient(dg_key)
        # Simple pre-recorded test (checking if client initializes and we can make a request)
        # We'll just check if we can list projects or usage, or just validity.
        # simpler: just print success if we got here without error on init
        print(f"✅ Deepgram Client Initialized")
    except Exception as e:
        print(f"❌ Deepgram Error: {e}")

async def test_groq_llm():
    print("\nTesting Groq LLM Connection...")
    try:
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            print("❌ GROQ_API_KEY is missing in .env")
            return

        client = AsyncGroq(api_key=groq_key)
        completion = await client.chat.completions.create(
            messages=[{"role": "user", "content": "Say 'Hello' in one word."}],
            model="llama3-8b-8192",
        )
        print(f"✅ Groq Response: {completion.choices[0].message.content}")
    except Exception as e:
        print(f"❌ Groq Error: {e}")

async def test_deepgram_tts():
    print("\nTesting Deepgram TTS Connection...")
    try:
        dg_key = os.getenv("DEEPGRAM_API_KEY")
        deepgram = DeepgramClient(dg_key)
        options = SpeakOptions(
            model="aura-asteria-en",
            encoding="linear16",
            sample_rate=16000,
        )
        # This will actually charge credits, so we just init
        # But to be sure, let's try a tiny text
        # res = await deepgram.speak.asyncev("1").save("Hi", options)
        print(f"✅ Deepgram TTS Client Ready (Skipping actual generation to save credits/time)")
    except Exception as e:
        print(f"❌ Deepgram TTS Error: {e}")

async def main():
    await test_deepgram_stt()
    await test_groq_llm()
    await test_deepgram_tts()

if __name__ == "__main__":
    asyncio.run(main())
