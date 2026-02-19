"""
VoiceBot: Orchestrates real-time voice conversation over telephony media streams.
Uses raw WebSocket to Deepgram for STT, Groq for LLM, and Deepgram REST for TTS.
Provider-agnostic: works with Twilio, Telnyx, or any provider implementing TelephonyProvider.
"""

import os
import json
import base64
import asyncio
import httpx
import websockets
from groq import AsyncGroq
from dotenv import load_dotenv
from system_prompt import SYSTEM_PROMPT
from providers import TelephonyProvider

load_dotenv()

# Deepgram STT WebSocket URL
DEEPGRAM_STT_URL = (
    "wss://api.deepgram.com/v1/listen"
    "?model=nova-2-phonecall"
    "&language=en-US"
    "&encoding=mulaw"
    "&sample_rate=8000"
    "&smart_format=true"
    "&interim_results=true"
    "&endpointing=300"
    "&utterance_end_ms=1000"
)

# Deepgram TTS REST URL
DEEPGRAM_TTS_URL = (
    "https://api.deepgram.com/v1/speak"
    "?model=aura-asteria-en"
    "&encoding=mulaw"
    "&sample_rate=8000"
    "&container=none"
)


class VoiceBot:
    def __init__(self, provider: TelephonyProvider):
        self.provider = provider
        self.deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
        self.groq_api_key = os.getenv("GROQ_API_KEY")

        self.groq_client = AsyncGroq(api_key=self.groq_api_key)
        self.http_client = httpx.AsyncClient(timeout=30.0)

        # Telephony WebSocket & stream state
        self.telephony_ws = None
        self.stream_sid = None

        # Deepgram STT WebSocket
        self.dg_ws = None

        # Barge-in state
        self._current_response_task = None
        self._is_responding = False

        # Conversation history for multi-turn context
        self.conversation_history = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    async def start(self, telephony_websocket):
        """Entry point: starts listening on the telephony WebSocket."""
        self.telephony_ws = telephony_websocket
        print(f"🔌 Using provider: {self.provider.name}")

        try:
            async with websockets.connect(
                DEEPGRAM_STT_URL,
                additional_headers={"Authorization": f"Token {self.deepgram_api_key}"},
            ) as dg_ws:
                self.dg_ws = dg_ws
                print("✅ Deepgram STT connected")

                await asyncio.gather(
                    self._handle_telephony_messages(),
                    self._handle_deepgram_messages(),
                )
        except Exception as e:
            print(f"❌ Deepgram connection error: {e}")
        finally:
            await self.http_client.aclose()

    async def _handle_telephony_messages(self):
        """Reads messages from the telephony provider and forwards audio to Deepgram."""
        try:
            async for message in self.telephony_ws.iter_text():
                event_type, data = self.provider.parse_event(message)

                if event_type == "start":
                    self.stream_sid = data["stream_sid"]
                    print(f"📞 [{self.provider.name}] Stream started: {self.stream_sid}")

                elif event_type == "media":
                    audio_bytes = base64.b64decode(data["payload"])
                    try:
                        if self.dg_ws:
                            await self.dg_ws.send(audio_bytes)
                    except Exception:
                        pass

                elif event_type == "mark":
                    # Playback finished — safe to clear the responding flag
                    print(f"✅ [{self.provider.name}] Playback finished (mark received)")
                    self._is_responding = False

                elif event_type == "stop":
                    print(f"📞 [{self.provider.name}] Stream stopped")
                    try:
                        if self.dg_ws:
                            await self.dg_ws.close()
                    except Exception:
                        pass
                    break

        except Exception as e:
            print(f"❌ [{self.provider.name}] handler error: {e}")

    async def _handle_deepgram_messages(self):
        """Reads transcription results from Deepgram and triggers LLM + TTS."""
        try:
            async for msg in self.dg_ws:
                data = json.loads(msg)
                msg_type = data.get("type")

                if msg_type == "Results":
                    alternatives = data.get("channel", {}).get("alternatives", [])
                    if not alternatives:
                        continue

                    transcript = alternatives[0].get("transcript", "").strip()
                    is_final = data.get("is_final", False)

                    if not transcript:
                        continue

                    # Barge-in: user started speaking while AI is talking
                    if not is_final and self._is_responding:
                        print(f"🛑 Barge-in detected! User said: {transcript}")
                        await self._interrupt()
                        continue

                    if is_final:
                        print(f"🎤 User: {transcript}")
                        self._current_response_task = asyncio.create_task(
                            self._respond(transcript)
                        )

        except websockets.exceptions.ConnectionClosed:
            print("Deepgram STT connection closed")
        except Exception as e:
            print(f"❌ Deepgram listener error: {e}")

    async def _interrupt(self):
        """Cancel the active response and flush the telephony audio buffer."""
        # Cancel the running LLM/TTS task
        if self._current_response_task and not self._current_response_task.done():
            self._current_response_task.cancel()
            print("🛑 Cancelled active response task")

        # Tell the telephony provider to stop playing audio
        if self.stream_sid and self.telephony_ws:
            clear_msg = self.provider.format_clear_message(self.stream_sid)
            await self.telephony_ws.send_text(clear_msg)
            print(f"🛑 [{self.provider.name}] Audio buffer cleared")

        self._is_responding = False
        self._current_response_task = None

    async def _respond(self, user_text: str):
        """Gets LLM response and synthesizes speech back to the caller."""
        self._is_responding = True
        try:
            self.conversation_history.append({"role": "user", "content": user_text})

            chat_completion = await self.groq_client.chat.completions.create(
                messages=self.conversation_history,
                model="llama-3.1-8b-instant",
                temperature=0.7,
                max_tokens=150,
            )

            ai_text = chat_completion.choices[0].message.content
            print(f"🤖 AI: {ai_text}")

            self.conversation_history.append({"role": "assistant", "content": ai_text})

            await self._synthesize_and_send(ai_text)

        except asyncio.CancelledError:
            print("🛑 Response was interrupted by user")
            self._is_responding = False
        except Exception as e:
            print(f"❌ Response error: {e}")
            self._is_responding = False
        # NOTE: do NOT set _is_responding = False here on success.
        # It stays True until the telephony provider sends back a "mark"
        # event confirming playback is done (see _handle_telephony_messages).

    async def _synthesize_and_send(self, text: str):
        """Calls Deepgram TTS REST API and sends audio back via the telephony provider."""
        try:
            response = await self.http_client.post(
                DEEPGRAM_TTS_URL,
                headers={
                    "Authorization": f"Token {self.deepgram_api_key}",
                    "Content-Type": "application/json",
                },
                json={"text": text},
            )

            if response.status_code != 200:
                print(f"❌ Deepgram TTS error ({response.status_code}): {response.text}")
                return

            encoded_audio = base64.b64encode(response.content).decode("utf-8")

            # Use provider to format the audio response
            media_message = self.provider.format_audio_response(self.stream_sid, encoded_audio)
            await self.telephony_ws.send_text(media_message)

            # Send a mark so the provider tells us when playback finishes
            mark_message = self.provider.format_mark_message(self.stream_sid, "response_end")
            await self.telephony_ws.send_text(mark_message)
            print(f"🔊 [{self.provider.name}] Audio sent to caller (waiting for playback mark)")

        except Exception as e:
            print(f"❌ TTS/Send error: {e}")
            self._is_responding = False
